from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Order, Quote, Client, Product, StockMovement, ServiceRecord, Transaction, User
from datetime import date
import json

order_bp = Blueprint("orders", __name__)
ORDER_PREFIX = "OS"


def _get_user(user_id):
    return User.query.get(int(user_id))


def _find_order(order_id, user):
    if user.company_id:
        return Order.query.filter_by(id=order_id, company_id=user.company_id).first()
    return Order.query.filter_by(id=order_id, user_id=user.id).first()


def _find_quote(quote_id, user):
    if user.company_id:
        return Quote.query.filter_by(id=quote_id, company_id=user.company_id).first()
    return Quote.query.filter_by(id=quote_id, user_id=user.id).first()


def _find_client(client_id, user):
    if user.company_id:
        return Client.query.filter_by(id=client_id, company_id=user.company_id).first()
    return Client.query.filter_by(id=client_id, user_id=user.id).first()


def _next_order_number(user):
    if user.company_id:
        count = Order.query.filter_by(company_id=user.company_id).count() + 1
    else:
        count = Order.query.filter_by(user_id=user.id).count() + 1
    return f"{ORDER_PREFIX}-{date.today().year}-{count:03d}"


def _serialize_order(o):
    return {
        "id":             o.id,
        "number":         o.number,
        "status":         o.status,
        "origin":         o.origin,
        "notes":          o.notes,
        "payment_terms":  o.payment_terms,
        "discount":       o.discount,
        "items":          json.loads(o.items_json or "[]"),
        "subtotal":       o.subtotal,
        "total":          o.total,
        "created_at":     o.created_at,
        "finished_at":    o.finished_at,
        "client_id":      o.client_id,
        "client_name":    o.client.name if o.client else "",
        "quote_id":       o.quote_id,
        "transaction_id": o.transaction_id,
        "user_id":        o.user_id,
    }


@order_bp.route("/orders", methods=["GET"])
@jwt_required()
def get_orders():
    user = _get_user(get_jwt_identity())
    if user.company_id:
        orders = Order.query.filter_by(company_id=user.company_id).order_by(Order.id.desc()).all()
    else:
        orders = Order.query.filter_by(user_id=user.id).order_by(Order.id.desc()).all()
    return jsonify([_serialize_order(o) for o in orders]), 200


@order_bp.route("/orders/<int:order_id>", methods=["GET"])
@jwt_required()
def get_order(order_id):
    user = _get_user(get_jwt_identity())
    o    = _find_order(order_id, user)
    if not o:
        return jsonify({"msg": "Venda não encontrada"}), 404
    return jsonify(_serialize_order(o)), 200


@order_bp.route("/orders", methods=["POST"])
@jwt_required()
def create_order():
    user = _get_user(get_jwt_identity())
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Nenhum dado enviado"}), 400

    client_id = data.get("client_id")
    if not client_id:
        return jsonify({"msg": "Cliente é obrigatório"}), 400

    client = _find_client(client_id, user)
    if not client:
        return jsonify({"msg": "Cliente não encontrado"}), 404

    items    = data.get("items", [])
    discount = float(data.get("discount", 0))
    subtotal = sum(float(i.get("qty", 0)) * float(i.get("price", 0)) for i in items)
    total    = subtotal - subtotal * (discount / 100)

    new_order = Order(
        number        = _next_order_number(user),
        status        = data.get("status", "open"),
        origin        = "direct",
        notes         = data.get("notes", ""),
        payment_terms = data.get("payment_terms", ""),
        discount      = discount,
        items_json    = json.dumps(items),
        subtotal      = subtotal,
        total         = total,
        created_at    = str(date.today()),
        client_id     = client_id,
        quote_id      = None,
        user_id       = user.id,
        company_id    = user.company_id,
    )
    db.session.add(new_order)
    db.session.commit()
    return jsonify({"msg": "Venda criada com sucesso", "id": new_order.id, "number": new_order.number}), 201


@order_bp.route("/orders/from-quote/<int:quote_id>", methods=["POST"])
@jwt_required()
def create_order_from_quote(quote_id):
    user  = _get_user(get_jwt_identity())
    quote = _find_quote(quote_id, user)

    if not quote:
        return jsonify({"msg": "Orçamento não encontrado"}), 404
    if quote.status != "approved":
        return jsonify({"msg": "Apenas orçamentos aprovados podem gerar vendas"}), 400

    if user.company_id:
        existing = Order.query.filter_by(quote_id=quote_id, company_id=user.company_id).first()
    else:
        existing = Order.query.filter_by(quote_id=quote_id, user_id=user.id).first()

    if existing:
        return jsonify({"msg": "Já existe uma venda para este orçamento", "id": existing.id, "number": existing.number}), 200

    client_id = quote.client_id
    if not client_id:
        auto_client = Client(
            name       = quote.client_name,
            email      = quote.client_email or None,
            phone      = quote.client_phone or None,
            document   = quote.client_document or None,
            address    = quote.client_address or None,
            created_at = str(date.today()),
            user_id    = user.id,
            company_id = user.company_id,
        )
        db.session.add(auto_client)
        db.session.flush()
        client_id       = auto_client.id
        quote.client_id = client_id

    items = json.loads(quote.items_json or "[]")

    new_order = Order(
        number        = _next_order_number(user),
        status        = "open",
        origin        = "quote",
        notes         = quote.notes or "",
        payment_terms = quote.payment_terms or "",
        discount      = quote.discount,
        items_json    = json.dumps(items),
        subtotal      = quote.subtotal,
        total         = quote.total,
        created_at    = str(date.today()),
        client_id     = client_id,
        quote_id      = quote_id,
        user_id       = user.id,
        company_id    = user.company_id,
    )
    db.session.add(new_order)
    db.session.commit()
    return jsonify({"msg": "Venda criada a partir do orçamento", "id": new_order.id, "number": new_order.number}), 201


@order_bp.route("/orders/<int:order_id>", methods=["PUT"])
@jwt_required()
def update_order(order_id):
    user = _get_user(get_jwt_identity())
    o    = _find_order(order_id, user)

    if not o:
        return jsonify({"msg": "Venda não encontrada"}), 404
    if o.status == "done":
        return jsonify({"msg": "Vendas concluídas não podem ser editadas"}), 400

    data     = request.get_json()
    items    = data.get("items", json.loads(o.items_json or "[]"))
    discount = float(data.get("discount", o.discount))
    subtotal = sum(float(i.get("qty", 0)) * float(i.get("price", 0)) for i in items)
    total    = subtotal - subtotal * (discount / 100)

    o.status        = data.get("status",        o.status)
    o.notes         = data.get("notes",         o.notes)
    o.payment_terms = data.get("payment_terms", o.payment_terms)
    o.discount      = discount
    o.items_json    = json.dumps(items)
    o.subtotal      = subtotal
    o.total         = total

    db.session.commit()
    return jsonify({"msg": "Venda atualizada com sucesso"}), 200


@order_bp.route("/orders/<int:order_id>/status", methods=["PATCH"])
@jwt_required()
def change_order_status(order_id):
    user = _get_user(get_jwt_identity())
    o    = _find_order(order_id, user)

    if not o:
        return jsonify({"msg": "Venda não encontrada"}), 404

    # ✅ vendedor só pode alterar status das próprias vendas
    if user.role == "seller" and o.user_id != user.id:
        return jsonify({"msg": "Você não tem permissão para alterar esta venda"}), 403

    data   = request.get_json()
    status = data.get("status")
    valid  = ["open", "in_progress", "done", "cancelled"]
    if status not in valid:
        return jsonify({"msg": f"Status inválido. Use: {valid}"}), 400

    old_status = o.status
    o.status   = status

    if status == "done" and old_status != "done":
        _conclude_order(o)
    elif old_status == "done" and status != "done":
        if o.transaction_id:
            t = Transaction.query.get(o.transaction_id)
            if t:
                db.session.delete(t)
            o.transaction_id = None
        o.finished_at = None

    db.session.commit()
    return jsonify({"msg": "Status atualizado", "status": status}), 200


@order_bp.route("/orders/<int:order_id>/complete", methods=["POST"])
@jwt_required()
def complete_order(order_id):
    user = _get_user(get_jwt_identity())
    o    = _find_order(order_id, user)

    if not o:
        return jsonify({"msg": "Venda não encontrada"}), 404

    # ✅ vendedor só pode concluir as próprias vendas
    if user.role == "seller" and o.user_id != user.id:
        return jsonify({"msg": "Você não tem permissão para concluir esta venda"}), 403

    if o.status == "done":
        return jsonify({"msg": "Esta venda já foi concluída"}), 400
    if o.status == "cancelled":
        return jsonify({"msg": "Vendas canceladas não podem ser concluídas"}), 400

    o.status = "done"
    _conclude_order(o)
    db.session.commit()

    return jsonify({"msg": f"Venda {o.number} concluída!", "transaction_id": o.transaction_id, "total": o.total}), 200


@order_bp.route("/orders/<int:order_id>", methods=["DELETE"])
@jwt_required()
def delete_order(order_id):
    user = _get_user(get_jwt_identity())
    o    = _find_order(order_id, user)

    if not o:
        return jsonify({"msg": "Venda não encontrada"}), 404

    # ✅ vendedor só pode deletar as próprias vendas
    if user.role == "seller" and o.user_id != user.id:
        return jsonify({"msg": "Você não tem permissão para remover esta venda"}), 403

    if o.transaction_id:
        t = Transaction.query.get(o.transaction_id)
        if t:
            db.session.delete(t)

    db.session.delete(o)
    db.session.commit()
    return jsonify({"msg": "Venda removida com sucesso"}), 200


# =========================
# HELPER — CONCLUIR VENDA
# =========================

def _conclude_order(o):
    """Cria transação, baixa estoque e registra serviços.
    ✅ Usa sempre o user_id da ORDEM, não de quem está concluindo.
    """
    o.finished_at = str(date.today())
    items = json.loads(o.items_json or "[]")

    # ✅ usa o dono da venda, não o usuário logado
    order_user = User.query.get(o.user_id)
    if not order_user:
        return

    client_name = o.client.name if o.client else "Cliente"
    transaction = Transaction(
        description = f"[Venda] {o.number} — {client_name}",
        amount      = o.total,
        type        = "income",
        category    = "Vendas",
        date        = str(date.today()),
        source      = "sale",
        user_id     = order_user.id,
        company_id  = order_user.company_id,
    )
    db.session.add(transaction)
    db.session.flush()
    o.transaction_id = transaction.id

    for item in items:
        product_id = item.get("product_id")
        if not product_id:
            continue
        product = Product.query.get(product_id)
        if not product:
            continue

        qty = float(item.get("qty", 0))

        if product.type == "product":
            product.stock_qty = max(0, product.stock_qty - qty)
            movement = StockMovement(
                type       = "out",
                qty        = qty,
                cost       = None,
                reason     = f"Venda {o.number}",
                date       = str(date.today()),
                product_id = product_id,
                order_id   = o.id,
                user_id    = order_user.id,
                company_id = order_user.company_id,
            )
            db.session.add(movement)

        elif product.type == "service":
            product.services_count += 1
            record = ServiceRecord(
                date         = str(date.today()),
                duration_min = None,
                amount       = float(item.get("price", product.price)) * qty,
                notes        = f"Venda {o.number}",
                product_id   = product_id,
                client_id    = o.client_id,
                order_id     = o.id,
                user_id      = order_user.id,
                company_id   = order_user.company_id,
            )
            db.session.add(record)