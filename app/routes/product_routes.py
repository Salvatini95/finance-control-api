from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Product

product_bp = Blueprint("products", __name__)


# =========================
# LISTAR PRODUTOS/SERVIÇOS
# =========================

@product_bp.route("/products", methods=["GET"])
@jwt_required()
def get_products():
    user_id = int(get_jwt_identity())
    products = Product.query.filter_by(user_id=user_id).order_by(Product.name).all()
    return jsonify([_serialize(p) for p in products]), 200


# =========================
# BUSCAR UM PRODUTO
# =========================

@product_bp.route("/products/<int:product_id>", methods=["GET"])
@jwt_required()
def get_product(product_id):
    user_id = int(get_jwt_identity())
    p = Product.query.filter_by(id=product_id, user_id=user_id).first()
    if not p:
        return jsonify({"msg": "Produto não encontrado"}), 404
    return jsonify(_serialize(p)), 200


# =========================
# CRIAR PRODUTO/SERVIÇO
# =========================

@product_bp.route("/products", methods=["POST"])
@jwt_required()
def create_product():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return jsonify({"msg": "Nenhum dado enviado"}), 400

    name  = data.get("name", "").strip()
    price = data.get("price")
    cost  = data.get("cost", 0)
    type_ = data.get("type", "service")

    if not name:
        return jsonify({"msg": "Nome é obrigatório"}), 400
    if price is None:
        return jsonify({"msg": "Preço é obrigatório"}), 400
    if type_ not in ["product", "service"]:
        return jsonify({"msg": "Tipo deve ser 'product' ou 'service'"}), 400

    p = Product(
        name        = name,
        description = data.get("description", "").strip(),
        type        = type_,
        unit        = data.get("unit", "un").strip(),
        cost        = float(cost),
        price       = float(price),
        category    = data.get("category", "").strip(),
        active      = data.get("active", True),
        user_id     = user_id,
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({"msg": "Produto criado com sucesso", "id": p.id}), 201


# =========================
# ATUALIZAR PRODUTO
# =========================

@product_bp.route("/products/<int:product_id>", methods=["PUT"])
@jwt_required()
def update_product(product_id):
    user_id = int(get_jwt_identity())
    p = Product.query.filter_by(id=product_id, user_id=user_id).first()
    if not p:
        return jsonify({"msg": "Produto não encontrado"}), 404

    data = request.get_json()
    p.name        = data.get("name",        p.name)
    p.description = data.get("description", p.description)
    p.type        = data.get("type",        p.type)
    p.unit        = data.get("unit",        p.unit)
    p.cost        = float(data.get("cost",  p.cost))
    p.price       = float(data.get("price", p.price))
    p.category    = data.get("category",    p.category)
    p.active      = data.get("active",      p.active)

    db.session.commit()
    return jsonify({"msg": "Produto atualizado com sucesso"}), 200


# =========================
# ATIVAR / DESATIVAR
# =========================

@product_bp.route("/products/<int:product_id>/toggle", methods=["PATCH"])
@jwt_required()
def toggle_product(product_id):
    user_id = int(get_jwt_identity())
    p = Product.query.filter_by(id=product_id, user_id=user_id).first()
    if not p:
        return jsonify({"msg": "Produto não encontrado"}), 404
    p.active = not p.active
    db.session.commit()
    return jsonify({"msg": "Status alterado", "active": p.active}), 200


# =========================
# DELETAR PRODUTO
# =========================

@product_bp.route("/products/<int:product_id>", methods=["DELETE"])
@jwt_required()
def delete_product(product_id):
    user_id = int(get_jwt_identity())
    p = Product.query.filter_by(id=product_id, user_id=user_id).first()
    if not p:
        return jsonify({"msg": "Produto não encontrado"}), 404
    db.session.delete(p)
    db.session.commit()
    return jsonify({"msg": "Produto removido com sucesso"}), 200


# =========================
# HELPER
# =========================

def _serialize(p):
    return {
        "id":          p.id,
        "name":        p.name,
        "description": p.description,
        "type":        p.type,
        "unit":        p.unit,
        "cost":        p.cost,
        "price":       p.price,
        "profit":      p.profit,
        "margin":      p.margin,
        "category":    p.category,
        "active":      p.active,
    }