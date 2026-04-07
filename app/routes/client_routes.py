from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Client, User
from datetime import date

client_bp = Blueprint("clients", __name__)


def _get_user(user_id):
    return User.query.get(int(user_id))


@client_bp.route("/clients", methods=["GET"])
@jwt_required()
def get_clients():
    user = _get_user(get_jwt_identity())

    if user.company_id:
        clients = Client.query.filter_by(company_id=user.company_id).order_by(Client.name).all()
    else:
        clients = Client.query.filter_by(user_id=user.id).order_by(Client.name).all()

    return jsonify([{
        "id":         c.id,
        "name":       c.name,
        "email":      c.email,
        "phone":      c.phone,
        "document":   c.document,
        "address":    c.address,
        "notes":      c.notes,
        "created_at": c.created_at,
    } for c in clients]), 200


@client_bp.route("/clients/<int:client_id>", methods=["GET"])
@jwt_required()
def get_client(client_id):
    user = _get_user(get_jwt_identity())
    c    = Client.query.filter_by(id=client_id, user_id=user.id).first()

    if not c:
        return jsonify({"msg": "Cliente não encontrado"}), 404

    quotes = [{"id": q.id, "number": q.number, "status": q.status, "total": q.total, "created_at": q.created_at} for q in c.quotes]
    orders = [{"id": o.id, "number": o.number, "status": o.status, "total": o.total, "created_at": o.created_at} for o in c.orders]

    return jsonify({
        "id":         c.id,
        "name":       c.name,
        "email":      c.email,
        "phone":      c.phone,
        "document":   c.document,
        "address":    c.address,
        "notes":      c.notes,
        "created_at": c.created_at,
        "quotes":     quotes,
        "orders":     orders,
    }), 200


@client_bp.route("/clients", methods=["POST"])
@jwt_required()
def create_client():
    user = _get_user(get_jwt_identity())
    data = request.get_json()

    if not data:
        return jsonify({"msg": "Nenhum dado enviado"}), 400

    name = data.get("name", "").strip()
    if not name:
        return jsonify({"msg": "Nome é obrigatório"}), 400

    new_client = Client(
        name       = name,
        email      = data.get("email",    "").strip() or None,
        phone      = data.get("phone",    "").strip() or None,
        document   = data.get("document", "").strip() or None,
        address    = data.get("address",  "").strip() or None,
        notes      = data.get("notes",    "").strip() or None,
        created_at = str(date.today()),
        user_id    = user.id,
        company_id = user.company_id,
    )
    db.session.add(new_client)
    db.session.commit()
    return jsonify({"msg": "Cliente criado com sucesso", "id": new_client.id}), 201


@client_bp.route("/clients/<int:client_id>", methods=["PUT"])
@jwt_required()
def update_client(client_id):
    user = _get_user(get_jwt_identity())
    c    = Client.query.filter_by(id=client_id, user_id=user.id).first()

    if not c:
        return jsonify({"msg": "Cliente não encontrado"}), 404

    data   = request.get_json()
    c.name     = data.get("name",     c.name).strip()
    c.email    = data.get("email",    c.email)
    c.phone    = data.get("phone",    c.phone)
    c.document = data.get("document", c.document)
    c.address  = data.get("address",  c.address)
    c.notes    = data.get("notes",    c.notes)

    db.session.commit()
    return jsonify({"msg": "Cliente atualizado com sucesso"}), 200


@client_bp.route("/clients/<int:client_id>", methods=["DELETE"])
@jwt_required()
def delete_client(client_id):
    user = _get_user(get_jwt_identity())
    c    = Client.query.filter_by(id=client_id, user_id=user.id).first()

    if not c:
        return jsonify({"msg": "Cliente não encontrado"}), 404

    db.session.delete(c)
    db.session.commit()
    return jsonify({"msg": "Cliente removido com sucesso"}), 200