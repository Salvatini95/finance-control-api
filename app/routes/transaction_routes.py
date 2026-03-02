from flask import Blueprint, request, jsonify
from app import db
from app.models import Transaction
from flask_jwt_extended import jwt_required, get_jwt_identity


transaction_bp = Blueprint("transactions", __name__, url_prefix="/transactions")


# =====================================
# CREATE TRANSACTION (PROTEGIDA)
# =====================================

@transaction_bp.route("/", methods=["POST"])
@jwt_required()
def create_transaction():

    user_id = int(get_jwt_identity())  # converter para int

    data = request.get_json()

    description = data.get("description")
    amount = data.get("amount")
    type = data.get("type")  # income ou expense

    if not description or not amount or not type:
        return jsonify({"error": "Todos os campos são obrigatórios"}), 400

    if type not in ["income", "expense"]:
        return jsonify({"error": "Tipo deve ser 'income' ou 'expense'"}), 400

    new_transaction = Transaction(
        description=description,
        amount=amount,
        type=type,
        user_id=user_id
    )

    db.session.add(new_transaction)
    db.session.commit()

    return jsonify({"message": "Transação criada com sucesso"}), 201


# =====================================
# LIST TRANSACTIONS (PROTEGIDA)
# =====================================

@transaction_bp.route("/", methods=["GET"])
@jwt_required()
def list_transactions():

    user_id = int(get_jwt_identity())

    transactions = Transaction.query.filter_by(user_id=user_id).all()

    result = []

    for t in transactions:
        result.append({
            "id": t.id,
            "description": t.description,
            "amount": t.amount,
            "type": t.type,
            "created_at": t.created_at
        })

    return jsonify(result), 200