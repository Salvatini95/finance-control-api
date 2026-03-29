import json
from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Quote, User

quote_bp = Blueprint("quotes", __name__)


# =========================
# LISTAR ORÇAMENTOS
# =========================

@quote_bp.route("/quotes", methods=["GET"])
@jwt_required()
def get_quotes():
    user_id = int(get_jwt_identity())
    quotes  = Quote.query.filter_by(user_id=user_id).order_by(Quote.id.desc()).all()
    return jsonify([_serialize(q) for q in quotes]), 200


# =========================
# BUSCAR UM ORÇAMENTO
# =========================

@quote_bp.route("/quotes/<int:quote_id>", methods=["GET"])
@jwt_required()
def get_quote(quote_id):
    user_id = int(get_jwt_identity())
    q = Quote.query.filter_by(id=quote_id, user_id=user_id).first()
    if not q:
        return jsonify({"msg": "Orçamento não encontrado"}), 404
    return jsonify(_serialize(q)), 200


# =========================
# CRIAR ORÇAMENTO
# =========================

@quote_bp.route("/quotes", methods=["POST"])
@jwt_required()
def create_quote():
    user_id = int(get_jwt_identity())
    data    = request.get_json()

    if not data:
        return jsonify({"msg": "Nenhum dado enviado"}), 400

    client_name = data.get("client_name", "").strip()
    if not client_name:
        return jsonify({"msg": "Nome do cliente é obrigatório"}), 400

    # gera número sequencial automático
    last = Quote.query.filter_by(user_id=user_id).order_by(Quote.id.desc()).first()
    seq  = (last.id + 1) if last else 1
    number = f"ORC-{date.today().year}-{seq:04d}"

    items    = data.get("items", [])
    subtotal = sum(float(i.get("qty", 1)) * float(i.get("price", 0)) for i in items)
    discount = float(data.get("discount", 0))
    total    = subtotal * (1 - discount / 100)

    q = Quote(
        number          = number,
        client_name     = client_name,
        client_email    = data.get("client_email",    "").strip(),
        client_phone    = data.get("client_phone",    "").strip(),
        client_document = data.get("client_document", "").strip(),
        client_address  = data.get("client_address",  "").strip(),
        status          = data.get("status",          "draft"),
        valid_until     = data.get("valid_until",     ""),
        payment_terms   = data.get("payment_terms",   "").strip(),
        notes           = data.get("notes",           "").strip(),
        discount        = discount,
        items_json      = json.dumps(items, ensure_ascii=False),
        subtotal        = subtotal,
        total           = total,
        created_at      = str(date.today()),
        user_id         = user_id,
    )
    db.session.add(q)
    db.session.commit()
    return jsonify({"msg": "Orçamento criado com sucesso", "id": q.id, "number": q.number}), 201


# =========================
# ATUALIZAR ORÇAMENTO
# =========================

@quote_bp.route("/quotes/<int:quote_id>", methods=["PUT"])
@jwt_required()
def update_quote(quote_id):
    user_id = int(get_jwt_identity())
    q = Quote.query.filter_by(id=quote_id, user_id=user_id).first()
    if not q:
        return jsonify({"msg": "Orçamento não encontrado"}), 404

    data = request.get_json()

    items    = data.get("items", json.loads(q.items_json))
    subtotal = sum(float(i.get("qty", 1)) * float(i.get("price", 0)) for i in items)
    discount = float(data.get("discount", q.discount))
    total    = subtotal * (1 - discount / 100)

    q.client_name     = data.get("client_name",     q.client_name)
    q.client_email    = data.get("client_email",    q.client_email)
    q.client_phone    = data.get("client_phone",    q.client_phone)
    q.client_document = data.get("client_document", q.client_document)
    q.client_address  = data.get("client_address",  q.client_address)
    q.status          = data.get("status",          q.status)
    q.valid_until     = data.get("valid_until",     q.valid_until)
    q.payment_terms   = data.get("payment_terms",   q.payment_terms)
    q.notes           = data.get("notes",           q.notes)
    q.discount        = discount
    q.items_json      = json.dumps(items, ensure_ascii=False)
    q.subtotal        = subtotal
    q.total           = total

    db.session.commit()
    return jsonify({"msg": "Orçamento atualizado com sucesso"}), 200


# =========================
# ALTERAR STATUS
# =========================

@quote_bp.route("/quotes/<int:quote_id>/status", methods=["PATCH"])
@jwt_required()
def update_status(quote_id):
    user_id = int(get_jwt_identity())
    q = Quote.query.filter_by(id=quote_id, user_id=user_id).first()
    if not q:
        return jsonify({"msg": "Orçamento não encontrado"}), 404

    data   = request.get_json()
    status = data.get("status", "")
    valid  = ["draft", "sent", "approved", "rejected", "cancelled"]
    if status not in valid:
        return jsonify({"msg": f"Status inválido. Use: {valid}"}), 400

    q.status = status
    db.session.commit()
    return jsonify({"msg": "Status atualizado", "status": q.status}), 200


# =========================
# DELETAR ORÇAMENTO
# =========================

@quote_bp.route("/quotes/<int:quote_id>", methods=["DELETE"])
@jwt_required()
def delete_quote(quote_id):
    user_id = int(get_jwt_identity())
    q = Quote.query.filter_by(id=quote_id, user_id=user_id).first()
    if not q:
        return jsonify({"msg": "Orçamento não encontrado"}), 404
    db.session.delete(q)
    db.session.commit()
    return jsonify({"msg": "Orçamento removido com sucesso"}), 200


# =========================
# DADOS DA EMPRESA (logo, nome, cnpj, endereço)
# =========================

@quote_bp.route("/company", methods=["GET"])
@jwt_required()
def get_company():
    user_id = int(get_jwt_identity())
    user    = User.query.get(user_id)
    return jsonify({
        "company_name":    user.company_name,
        "company_cnpj":    user.company_cnpj,
        "company_address": user.company_address,
        "company_logo":    user.company_logo,
    }), 200


@quote_bp.route("/company", methods=["PUT"])
@jwt_required()
def update_company():
    user_id = int(get_jwt_identity())
    user    = User.query.get(user_id)
    data    = request.get_json()

    user.company_name    = data.get("company_name",    user.company_name)
    user.company_cnpj    = data.get("company_cnpj",    user.company_cnpj)
    user.company_address = data.get("company_address", user.company_address)
    if "company_logo" in data:
        user.company_logo = data["company_logo"]   # base64 string

    db.session.commit()
    return jsonify({"msg": "Dados da empresa atualizados"}), 200


# =========================
# HELPER
# =========================

def _serialize(q):
    return {
        "id":              q.id,
        "number":          q.number,
        "client_name":     q.client_name,
        "client_email":    q.client_email,
        "client_phone":    q.client_phone,
        "client_document": q.client_document,
        "client_address":  q.client_address,
        "status":          q.status,
        "valid_until":     q.valid_until,
        "payment_terms":   q.payment_terms,
        "notes":           q.notes,
        "discount":        q.discount,
        "items":           json.loads(q.items_json or "[]"),
        "subtotal":        q.subtotal,
        "total":           q.total,
        "created_at":      q.created_at,
    }