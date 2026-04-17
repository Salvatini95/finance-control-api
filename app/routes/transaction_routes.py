from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Transaction, User, Order

transaction_bp = Blueprint("transactions", __name__)


def _get_user(user_id):
    return User.query.get(int(user_id))


def _find_transaction(transaction_id, user):
    if user.company_id:
        return Transaction.query.filter_by(id=transaction_id, company_id=user.company_id).first()
    return Transaction.query.filter_by(id=transaction_id, user_id=user.id).first()


def _is_admin(user):
    return user.role == "admin"


@transaction_bp.route("/transactions", methods=["GET"])
@jwt_required()
def get_transactions():
    user          = _get_user(get_jwt_identity())
    source_filter = request.args.get("source", "all")
    type_filter   = request.args.get("type",   "all")

    if user.company_id:
        query = Transaction.query.filter_by(company_id=user.company_id)
    else:
        query = Transaction.query.filter_by(user_id=user.id)

    if source_filter != "all":
        query = query.filter_by(source=source_filter)
    if type_filter != "all":
        query = query.filter_by(type=type_filter)

    transactions = query.order_by(Transaction.date.desc()).all()

    # Monta lookup de order_number por transaction_id para transações de venda
    order_map = {}
    if user.company_id:
        orders = Order.query.filter_by(company_id=user.company_id).filter(
            Order.transaction_id.isnot(None)
        ).all()
        for o in orders:
            order_map[o.transaction_id] = {"order_id": o.id, "order_number": o.number}

    return jsonify([{
        "id":           t.id,
        "description":  t.description,
        "amount":       t.amount,
        "type":         t.type,
        "category":     t.category,
        "date":         t.date,
        "source":       t.source,
        # ✅ campos novos para link clicável
        "order_id":     order_map.get(t.id, {}).get("order_id"),
        "order_number": order_map.get(t.id, {}).get("order_number"),
    } for t in transactions]), 200


@transaction_bp.route("/transactions", methods=["POST"])
@jwt_required()
def create_transaction():
    user = _get_user(get_jwt_identity())
    data = request.get_json()

    if not data:
        return jsonify({"msg": "Nenhum dado enviado"}), 400

    description = data.get("description", "").strip()
    amount      = data.get("amount")
    type_       = data.get("type", "").strip()

    if not description or not amount or not type_:
        return jsonify({"msg": "Descrição, valor e tipo são obrigatórios"}), 400
    if type_ not in ["income", "expense"]:
        return jsonify({"msg": "Tipo deve ser 'income' ou 'expense'"}), 400

    t = Transaction(
        description = description,
        amount      = float(amount),
        type        = type_,
        category    = data.get("category", "").strip() or None,
        date        = data.get("date") or None,
        source      = data.get("source", "manual"),
        user_id     = user.id,
        company_id  = user.company_id,
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({"msg": "Transação criada", "id": t.id}), 201


@transaction_bp.route("/transactions/<int:transaction_id>", methods=["PUT"])
@jwt_required()
def update_transaction(transaction_id):
    user = _get_user(get_jwt_identity())
    t    = _find_transaction(transaction_id, user)

    if not t:
        return jsonify({"msg": "Transação não encontrada"}), 404

    # Admin pode editar qualquer transação; outros só manual
    if not _is_admin(user) and t.source != "manual":
        return jsonify({"msg": "Apenas admins podem editar transações automáticas"}), 403

    data          = request.get_json()
    t.description = data.get("description", t.description)
    t.amount      = float(data.get("amount", t.amount))
    t.type        = data.get("type",        t.type)
    t.category    = data.get("category",    t.category)
    t.date        = data.get("date",        t.date)

    db.session.commit()
    return jsonify({"msg": "Transação atualizada"}), 200


@transaction_bp.route("/transactions/<int:transaction_id>", methods=["DELETE"])
@jwt_required()
def delete_transaction(transaction_id):
    user = _get_user(get_jwt_identity())
    t    = _find_transaction(transaction_id, user)

    if not t:
        return jsonify({"msg": "Transação não encontrada"}), 404

    # Admin pode deletar qualquer transação; outros só manual
    if not _is_admin(user) and t.source != "manual":
        return jsonify({"msg": "Apenas admins podem remover transações automáticas"}), 403

    # Se for transação de venda, desvincula a order (não deleta a venda)
    if t.source == "sale":
        order = Order.query.filter_by(transaction_id=t.id, company_id=user.company_id).first()
        if order:
            order.transaction_id = None

    db.session.delete(t)
    db.session.commit()
    return jsonify({"msg": "Transação removida"}), 200


@transaction_bp.route("/transactions/<int:transaction_id>/cancel", methods=["PATCH"])
@jwt_required()
def cancel_transaction(transaction_id):
    """
    Cancela uma transação de venda sem deletar —
    muda source para 'cancelled' e desvincula a order.
    Somente admin.
    """
    user = _get_user(get_jwt_identity())
    if not _is_admin(user):
        return jsonify({"msg": "Apenas admins podem cancelar transações"}), 403

    t = _find_transaction(transaction_id, user)
    if not t:
        return jsonify({"msg": "Transação não encontrada"}), 404

    # Desvincula order se existir
    if t.source == "sale":
        order = Order.query.filter_by(transaction_id=t.id, company_id=user.company_id).first()
        if order:
            order.transaction_id = None
            order.status         = "open"  # reabre a venda

    t.source = "cancelled"
    db.session.commit()
    return jsonify({"msg": "Transação cancelada. Venda reaberta."}), 200