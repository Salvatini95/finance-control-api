from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Product, User, StockMovement, ServiceRecord, Quote, Order
from datetime import date

product_bp = Blueprint("products", __name__)


def _get_user(user_id):
    return User.query.get(int(user_id))


def _find_product(product_id, user):
    if user.company_id:
        return Product.query.filter_by(id=product_id, company_id=user.company_id).first()
    return Product.query.filter_by(id=product_id, user_id=user.id).first()


def _serialize(p):
    return {
        "id":             p.id,
        "sku":            p.sku,
        "name":           p.name,
        "description":    p.description,
        "type":           p.type,
        "unit":           p.unit,
        "cost":           p.cost,
        "price":          p.price,
        "profit":         p.profit,
        "margin":         p.margin,
        "category":       p.category,
        "active":         p.active,
        "stock_qty":      p.stock_qty,
        "stock_min":      p.stock_min,
        "stock_avg_cost": p.stock_avg_cost,
        "services_count": p.services_count,
    }


@product_bp.route("/products", methods=["GET"])
@jwt_required()
def get_products():
    user = _get_user(get_jwt_identity())
    if user.company_id:
        products = Product.query.filter_by(company_id=user.company_id).order_by(Product.name).all()
    else:
        products = Product.query.filter_by(user_id=user.id).order_by(Product.name).all()
    return jsonify([_serialize(p) for p in products]), 200


@product_bp.route("/products/<int:product_id>", methods=["GET"])
@jwt_required()
def get_product(product_id):
    user = _get_user(get_jwt_identity())
    p    = _find_product(product_id, user)
    if not p:
        return jsonify({"msg": "Produto não encontrado"}), 404
    return jsonify(_serialize(p)), 200


@product_bp.route("/products", methods=["POST"])
@jwt_required()
def create_product():
    user = _get_user(get_jwt_identity())
    data = request.get_json()

    if not data:
        return jsonify({"msg": "Nenhum dado enviado"}), 400

    name  = data.get("name", "").strip()
    price = data.get("price")
    type_ = data.get("type", "service")

    if not name:
        return jsonify({"msg": "Nome é obrigatório"}), 400
    if price is None:
        return jsonify({"msg": "Preço é obrigatório"}), 400
    if type_ not in ["product", "service"]:
        return jsonify({"msg": "Tipo deve ser 'product' ou 'service'"}), 400

    stock_qty_initial = float(data.get("stock_qty_initial", 0) or 0)
    cost_val          = float(data.get("cost", 0) or 0)

    p = Product(
        name        = name,
        sku         = data.get("sku", "").strip() or None,
        description = data.get("description", "").strip(),
        type        = type_,
        unit        = data.get("unit", "un").strip(),
        cost        = cost_val,
        price       = float(price),
        category    = data.get("category", "").strip(),
        active      = data.get("active", True),
        stock_min   = float(data.get("stock_min", 0) or 0),
        stock_qty   = stock_qty_initial,
        user_id     = user.id,
        company_id  = user.company_id,
    )

    if type_ == "product" and stock_qty_initial > 0:
        p.stock_avg_cost = cost_val

    db.session.add(p)
    db.session.flush()

    if type_ == "product" and stock_qty_initial > 0:
        mov = StockMovement(
            type       = "in",
            qty        = stock_qty_initial,
            cost       = cost_val if cost_val > 0 else None,
            reason     = "Estoque Inicial",
            date       = str(date.today()),
            product_id = p.id,
            user_id    = user.id,
            company_id = user.company_id,
        )
        db.session.add(mov)

    db.session.commit()
    return jsonify({"msg": "Produto criado com sucesso", "id": p.id}), 201


@product_bp.route("/products/<int:product_id>", methods=["PUT"])
@jwt_required()
def update_product(product_id):
    user = _get_user(get_jwt_identity())
    p    = _find_product(product_id, user)
    if not p:
        return jsonify({"msg": "Produto não encontrado"}), 404

    data          = request.get_json()
    p.name        = data.get("name",        p.name)
    p.sku         = data.get("sku",         p.sku)
    p.description = data.get("description", p.description)
    p.type        = data.get("type",        p.type)
    p.unit        = data.get("unit",        p.unit)
    p.cost        = float(data.get("cost",  p.cost))
    p.price       = float(data.get("price", p.price))
    p.category    = data.get("category",    p.category)
    p.active      = data.get("active",      p.active)
    p.stock_min   = float(data.get("stock_min", p.stock_min))

    db.session.commit()
    return jsonify({"msg": "Produto atualizado com sucesso"}), 200


@product_bp.route("/products/<int:product_id>/toggle", methods=["PATCH"])
@jwt_required()
def toggle_product(product_id):
    user = _get_user(get_jwt_identity())
    p    = _find_product(product_id, user)
    if not p:
        return jsonify({"msg": "Produto não encontrado"}), 404
    p.active = not p.active
    db.session.commit()
    return jsonify({"msg": "Status alterado", "active": p.active}), 200


@product_bp.route("/products/<int:product_id>", methods=["DELETE"])
@jwt_required()
def delete_product(product_id):
    user = _get_user(get_jwt_identity())
    p    = _find_product(product_id, user)
    if not p:
        return jsonify({"msg": "Produto não encontrado"}), 404

    # ── Remove dependências antes de deletar o produto ──────────────
    # 1. Movimentações de estoque
    StockMovement.query.filter_by(product_id=p.id).delete()

    # 2. Registros de serviço
    ServiceRecord.query.filter_by(product_id=p.id).delete()

    # 3. Orçamentos que referenciam este produto via items_json
    #    Não deletamos o orçamento — apenas limpamos a FK direta se existir
    #    (Quote não tem product_id direto, apenas em items_json — sem FK real)

    # 4. Ordens de serviço: idem — product_id não é FK direta em Order

    # 5. Deleta o produto
    db.session.delete(p)
    db.session.commit()

    return jsonify({"msg": "Produto removido com sucesso"}), 200