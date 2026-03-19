from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import Transaction

transaction_bp = Blueprint("transactions", __name__)


# =========================
# LISTAR TRANSAÇÕES
# =========================
@transaction_bp.route("/transactions", methods=["GET"])
@jwt_required()
def get_transactions():

    user_id = get_jwt_identity()

    transactions = Transaction.query.filter_by(user_id=user_id).all()

    result = []

    for t in transactions:
        result.append({
            "id": t.id,
            "description": t.description,
            "amount": float(t.amount),
            "type": t.type,
            "category": t.category,
            "date": t.date
        })

    return jsonify(result), 200


# =========================
# CRIAR TRANSAÇÃO
# =========================
@transaction_bp.route("/transactions", methods=["POST"])
@jwt_required()
def create_transaction():

    user_id = get_jwt_identity()
    data = request.get_json()

    # 🔥 VALIDAÇÃO
    if not data:
        return jsonify({"msg": "Dados não enviados"}), 400

    if not data.get("description") or not data.get("amount") or not data.get("category") or not data.get("date"):
        return jsonify({"msg": "Campos obrigatórios faltando"}), 422

    try:
        new_transaction = Transaction(
            description=data.get("description"),
            amount=float(data.get("amount")),
            type=data.get("type"),
            category=data.get("category"),
            date=data.get("date"),
            user_id=user_id
        )

        db.session.add(new_transaction)
        db.session.commit()

        return jsonify({"msg": "Transação criada com sucesso"}), 201

    except Exception as e:
        return jsonify({"msg": "Erro ao criar transação", "error": str(e)}), 400


# =========================
# EDITAR TRANSAÇÃO
# =========================
@transaction_bp.route("/transactions/<int:id>", methods=["PUT"])
@jwt_required()
def update_transaction(id):

    user_id = get_jwt_identity()
    data = request.get_json()

    transaction = Transaction.query.filter_by(id=id, user_id=user_id).first()

    if not transaction:
        return jsonify({"msg": "Transação não encontrada"}), 404

    # 🔥 VALIDAÇÃO
    if not data:
        return jsonify({"msg": "Dados não enviados"}), 400

    if not data.get("description") or not data.get("amount") or not data.get("category") or not data.get("date"):
        return jsonify({"msg": "Campos obrigatórios faltando"}), 422

    try:
        transaction.description = data.get("description")
        transaction.amount = float(data.get("amount"))
        transaction.type = data.get("type")
        transaction.category = data.get("category")
        transaction.date = data.get("date")

        db.session.commit()

        return jsonify({"msg": "Transação atualizada com sucesso"}), 200

    except Exception as e:
        return jsonify({"msg": "Erro ao atualizar", "error": str(e)}), 400


# =========================
# DELETAR TRANSAÇÃO
# =========================
@transaction_bp.route("/transactions/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_transaction(id):

    user_id = get_jwt_identity()

    transaction = Transaction.query.filter_by(id=id, user_id=user_id).first()

    if not transaction:
        return jsonify({"msg": "Transação não encontrada"}), 404

    try:
        db.session.delete(transaction)
        db.session.commit()

        return jsonify({"msg": "Transação deletada com sucesso"}), 200

    except Exception as e:
        return jsonify({"msg": "Erro ao deletar", "error": str(e)}), 400