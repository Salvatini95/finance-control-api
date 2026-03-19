from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import Category


category_bp = Blueprint("category", __name__)


# =============================
# LISTAR CATEGORIAS
# =============================

@category_bp.route("/categories", methods=["GET"])
@jwt_required()
def get_categories():

    user_id = get_jwt_identity()

    categories = Category.query.filter_by(user_id=user_id).all()

    result = []

    for category in categories:

        result.append({
            "id": category.id,
            "name": category.name
        })

    return jsonify(result)


# =============================
# CRIAR CATEGORIA
# =============================

@category_bp.route("/categories", methods=["POST"])
@jwt_required()
def create_category():

    data = request.get_json()

    user_id = get_jwt_identity()

    category = Category(
        name=data["name"],
        user_id=user_id
    )

    db.session.add(category)

    db.session.commit()

    return jsonify({
        "message": "Categoria criada com sucesso"
    })


# =============================
# DELETAR CATEGORIA
# =============================

@category_bp.route("/categories/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_category(id):

    category = Category.query.get_or_404(id)

    db.session.delete(category)

    db.session.commit()

    return jsonify({
        "message": "Categoria deletada"
    })