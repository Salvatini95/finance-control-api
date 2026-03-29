from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Bill, Transaction
from datetime import date

bill_bp = Blueprint("bills", __name__)


# =========================
# LISTAR CONTAS
# =========================

@bill_bp.route("/bills", methods=["GET"])
@jwt_required()
def get_bills():

    user_id = int(get_jwt_identity())
    bills = Bill.query.filter_by(user_id=user_id).order_by(Bill.due_date).all()

    return jsonify([{
        "id": b.id,
        "description": b.description,
        "amount": b.amount,
        "type": b.type,
        "status": b.status,
        "due_date": b.due_date,
        "paid_date": b.paid_date,
        "category": b.category,
        "notes": b.notes,
        "transaction_id": b.transaction_id
    } for b in bills]), 200


# =========================
# CRIAR CONTA
# =========================

@bill_bp.route("/bills", methods=["POST"])
@jwt_required()
def create_bill():

    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return jsonify({"msg": "Nenhum dado enviado"}), 400

    description = data.get("description", "").strip()
    amount = data.get("amount")
    type_ = data.get("type", "").strip()
    due_date = data.get("due_date", "").strip()

    if not description or not amount or not type_ or not due_date:
        return jsonify({"msg": "Descrição, valor, tipo e vencimento são obrigatórios"}), 400

    if type_ not in ["payable", "receivable"]:
        return jsonify({"msg": "Tipo deve ser 'payable' ou 'receivable'"}), 400

    new_bill = Bill(
        description=description,
        amount=float(amount),
        type=type_,
        status=data.get("status", "pending"),
        due_date=due_date,
        paid_date=data.get("paid_date"),
        category=data.get("category", "").strip(),
        notes=data.get("notes", "").strip(),
        user_id=user_id,
        transaction_id=None
    )

    db.session.add(new_bill)
    db.session.commit()

    # Se criada já como paga, sincroniza transação
    if new_bill.status == "paid":
        _sync_transaction(new_bill, user_id)

    return jsonify({"msg": "Conta criada com sucesso", "id": new_bill.id}), 201


# =========================
# ATUALIZAR CONTA
# =========================

@bill_bp.route("/bills/<int:bill_id>", methods=["PUT"])
@jwt_required()
def update_bill(bill_id):

    user_id = int(get_jwt_identity())
    bill = Bill.query.filter_by(id=bill_id, user_id=user_id).first()

    if not bill:
        return jsonify({"msg": "Conta não encontrada"}), 404

    data = request.get_json()

    old_status = bill.status

    bill.description = data.get("description", bill.description)
    bill.amount      = float(data.get("amount", bill.amount))
    bill.type        = data.get("type", bill.type)
    bill.status      = data.get("status", bill.status)
    bill.due_date    = data.get("due_date", bill.due_date)
    bill.paid_date   = data.get("paid_date", bill.paid_date)
    bill.category    = data.get("category", bill.category)
    bill.notes       = data.get("notes", bill.notes)

    db.session.commit()

    # Se mudou para pago, sincroniza transação
    if old_status != "paid" and bill.status == "paid":
        _sync_transaction(bill, user_id)

    # Se voltou para pendente, remove transação vinculada
    if old_status == "paid" and bill.status != "paid":
        _remove_transaction(bill)

    return jsonify({"msg": "Conta atualizada com sucesso"}), 200


# =========================
# MARCAR COMO PAGO
# =========================

@bill_bp.route("/bills/<int:bill_id>/pay", methods=["PATCH"])
@jwt_required()
def pay_bill(bill_id):

    user_id = int(get_jwt_identity())
    bill = Bill.query.filter_by(id=bill_id, user_id=user_id).first()

    if not bill:
        return jsonify({"msg": "Conta não encontrada"}), 404

    bill.status    = "paid"
    bill.paid_date = str(date.today())

    db.session.commit()

    # Sincroniza transação automaticamente
    _sync_transaction(bill, user_id)

    return jsonify({"msg": "Conta marcada como paga e transação criada!"}), 200


# =========================
# DELETAR CONTA
# =========================

@bill_bp.route("/bills/<int:bill_id>", methods=["DELETE"])
@jwt_required()
def delete_bill(bill_id):

    user_id = int(get_jwt_identity())
    bill = Bill.query.filter_by(id=bill_id, user_id=user_id).first()

    if not bill:
        return jsonify({"msg": "Conta não encontrada"}), 404

    # Remove transação vinculada se existir
    _remove_transaction(bill)

    db.session.delete(bill)
    db.session.commit()

    return jsonify({"msg": "Conta removida com sucesso"}), 200


# =========================
# HELPERS DE SINCRONIZAÇÃO
# =========================

def _sync_transaction(bill, user_id):
    """Cria ou atualiza a transação vinculada à conta."""

    # Define o tipo da transação
    # payable (a pagar) → expense (saída)
    # receivable (a receber) → income (entrada)
    transaction_type = "expense" if bill.type == "payable" else "income"

    paid_date = bill.paid_date or str(date.today())

    if bill.transaction_id:
        # Atualiza transação existente
        transaction = Transaction.query.get(bill.transaction_id)
        if transaction:
            transaction.description = f"[Auto] {bill.description}"
            transaction.amount      = bill.amount
            transaction.type        = transaction_type
            transaction.category    = bill.category or "Contas"
            transaction.date        = paid_date
            db.session.commit()
            return

    # Cria nova transação
    new_transaction = Transaction(
        description = f"[Auto] {bill.description}",
        amount      = bill.amount,
        type        = transaction_type,
        category    = bill.category or "Contas",
        date        = paid_date,
        user_id     = user_id
    )

    db.session.add(new_transaction)
    db.session.flush()  # gera o ID antes do commit

    bill.transaction_id = new_transaction.id
    db.session.commit()


def _remove_transaction(bill):
    """Remove a transação vinculada à conta se existir."""
    if bill.transaction_id:
        transaction = Transaction.query.get(bill.transaction_id)
        if transaction:
            db.session.delete(transaction)
        bill.transaction_id = None
        db.session.commit()