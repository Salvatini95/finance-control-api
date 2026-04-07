from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Bill, Transaction, User
from datetime import date

bill_bp = Blueprint("bills", __name__)


def _get_user(user_id):
    return User.query.get(int(user_id))


@bill_bp.route("/bills", methods=["GET"])
@jwt_required()
def get_bills():
    user = _get_user(get_jwt_identity())

    if user.company_id:
        bills = Bill.query.filter_by(company_id=user.company_id).order_by(Bill.due_date).all()
    else:
        bills = Bill.query.filter_by(user_id=user.id).order_by(Bill.due_date).all()

    return jsonify([{
        "id":             b.id,
        "description":    b.description,
        "amount":         b.amount,
        "type":           b.type,
        "status":         b.status,
        "due_date":       b.due_date,
        "paid_date":      b.paid_date,
        "category":       b.category,
        "notes":          b.notes,
        "transaction_id": b.transaction_id,
    } for b in bills]), 200


@bill_bp.route("/bills", methods=["POST"])
@jwt_required()
def create_bill():
    user = _get_user(get_jwt_identity())
    data = request.get_json()

    if not data:
        return jsonify({"msg": "Nenhum dado enviado"}), 400

    description = data.get("description", "").strip()
    amount      = data.get("amount")
    type_       = data.get("type", "").strip()
    due_date    = data.get("due_date", "").strip()

    if not description or not amount or not type_ or not due_date:
        return jsonify({"msg": "Descrição, valor, tipo e vencimento são obrigatórios"}), 400
    if type_ not in ["payable", "receivable"]:
        return jsonify({"msg": "Tipo deve ser 'payable' ou 'receivable'"}), 400

    new_bill = Bill(
        description    = description,
        amount         = float(amount),
        type           = type_,
        status         = data.get("status", "pending"),
        due_date       = due_date,
        paid_date      = data.get("paid_date"),
        category       = data.get("category", "").strip(),
        notes          = data.get("notes", "").strip(),
        user_id        = user.id,
        company_id     = user.company_id,
        transaction_id = None,
    )
    db.session.add(new_bill)
    db.session.commit()

    if new_bill.status == "paid":
        _sync_transaction(new_bill, user)

    return jsonify({"msg": "Conta criada com sucesso", "id": new_bill.id}), 201


@bill_bp.route("/bills/<int:bill_id>", methods=["PUT"])
@jwt_required()
def update_bill(bill_id):
    user = _get_user(get_jwt_identity())
    bill = Bill.query.filter_by(id=bill_id, user_id=user.id).first()

    if not bill:
        return jsonify({"msg": "Conta não encontrada"}), 404

    data       = request.get_json()
    old_status = bill.status

    bill.description = data.get("description", bill.description)
    bill.amount      = float(data.get("amount", bill.amount))
    bill.type        = data.get("type",        bill.type)
    bill.status      = data.get("status",      bill.status)
    bill.due_date    = data.get("due_date",    bill.due_date)
    bill.paid_date   = data.get("paid_date",   bill.paid_date)
    bill.category    = data.get("category",    bill.category)
    bill.notes       = data.get("notes",       bill.notes)

    db.session.commit()

    if old_status != "paid" and bill.status == "paid":
        _sync_transaction(bill, user)
    if old_status == "paid" and bill.status != "paid":
        _remove_transaction(bill)

    return jsonify({"msg": "Conta atualizada com sucesso"}), 200


@bill_bp.route("/bills/<int:bill_id>/pay", methods=["PATCH"])
@jwt_required()
def pay_bill(bill_id):
    user = _get_user(get_jwt_identity())
    bill = Bill.query.filter_by(id=bill_id, user_id=user.id).first()

    if not bill:
        return jsonify({"msg": "Conta não encontrada"}), 404

    bill.status    = "paid"
    bill.paid_date = str(date.today())
    db.session.commit()

    _sync_transaction(bill, user)
    return jsonify({"msg": "Conta marcada como paga e transação criada!"}), 200


@bill_bp.route("/bills/<int:bill_id>", methods=["DELETE"])
@jwt_required()
def delete_bill(bill_id):
    user = _get_user(get_jwt_identity())
    bill = Bill.query.filter_by(id=bill_id, user_id=user.id).first()

    if not bill:
        return jsonify({"msg": "Conta não encontrada"}), 404

    _remove_transaction(bill)
    db.session.delete(bill)
    db.session.commit()
    return jsonify({"msg": "Conta removida com sucesso"}), 200


# =========================
# HELPERS
# =========================

def _sync_transaction(bill, user):
    transaction_type = "expense" if bill.type == "payable" else "income"
    paid_date        = bill.paid_date or str(date.today())

    if bill.transaction_id:
        t = Transaction.query.get(bill.transaction_id)
        if t:
            t.description = f"[Conta] {bill.description}"
            t.amount      = bill.amount
            t.type        = transaction_type
            t.category    = bill.category or "Contas"
            t.date        = paid_date
            t.source      = "bill"
            db.session.commit()
            return

    new_t = Transaction(
        description = f"[Conta] {bill.description}",
        amount      = bill.amount,
        type        = transaction_type,
        category    = bill.category or "Contas",
        date        = paid_date,
        source      = "bill",
        user_id     = user.id,
        company_id  = user.company_id,
    )
    db.session.add(new_t)
    db.session.flush()
    bill.transaction_id = new_t.id
    db.session.commit()


def _remove_transaction(bill):
    if bill.transaction_id:
        t = Transaction.query.get(bill.transaction_id)
        if t:
            db.session.delete(t)
        bill.transaction_id = None
        db.session.commit()