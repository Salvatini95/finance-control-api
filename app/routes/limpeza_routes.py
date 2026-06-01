from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import LimpezaServiceCard, LimpezaOccurrence, Order
from datetime import datetime

limpeza_bp = Blueprint("limpeza", __name__, url_prefix="/api/limpeza")


def _company_id():
    identity = get_jwt_identity()
    return identity.get("company_id") if isinstance(identity, dict) else None


@limpeza_bp.route("/card/<int:order_id>", methods=["GET"])
@jwt_required()
def obter_cartao(order_id):
    cid = _company_id()
    order = Order.query.filter_by(id=order_id, company_id=cid).first()
    if not order:
        return jsonify({"erro": "O.S não encontrada"}), 404
    card = LimpezaServiceCard.query.filter_by(order_id=order_id).first()
    if not card:
        card = LimpezaServiceCard(
            company_id=cid,
            order_id=order_id,
            client_id=order.client_id,
            mes=datetime.now().month,
            ano=datetime.now().year,
        )
        db.session.add(card)
        db.session.commit()
    occs = LimpezaOccurrence.query.filter_by(order_id=order_id).order_by(LimpezaOccurrence.created_at.desc()).all()
    return jsonify({"card": card.to_dict(), "ocorrencias": [o.to_dict() for o in occs]}), 200


@limpeza_bp.route("/card/<int:order_id>", methods=["PUT"])
@jwt_required()
def atualizar_cartao(order_id):
    cid = _company_id()
    order = Order.query.filter_by(id=order_id, company_id=cid).first()
    if not order:
        return jsonify({"erro": "O.S não encontrada"}), 404
    data = (request.get_json() or {}).get("card", {})
    card = LimpezaServiceCard.query.filter_by(order_id=order_id).first()
    if not card:
        card = LimpezaServiceCard(company_id=cid, order_id=order_id, client_id=order.client_id)
        db.session.add(card)
    for campo in ["frequencia", "mes", "ano", "dias_semana", "obs_contrato", "semanas"]:
        if campo in data:
            setattr(card, campo, data[campo])
    db.session.commit()
    return jsonify({"mensagem": "Salvo", "card": card.to_dict()}), 200


@limpeza_bp.route("/occurrence", methods=["POST"])
@jwt_required()
def registrar_ocorrencia():
    cid = _company_id()
    data = request.get_json() or {}
    order = Order.query.filter_by(id=data.get("order_id"), company_id=cid).first()
    if not order:
        return jsonify({"erro": "O.S não encontrada"}), 404
    occ = LimpezaOccurrence(
        company_id=cid,
        order_id=data["order_id"],
        tipo=data.get("tipo", ""),
        data=data.get("data", ""),
        hora=data.get("hora"),
        descricao=data.get("descricao", ""),
        reagendamento_data=data.get("reagendamento_data"),
        reagendamento_hora=data.get("reagendamento_hora"),
    )
    db.session.add(occ)
    db.session.commit()
    return jsonify({"mensagem": "Registrado", "ocorrencia": occ.to_dict()}), 201


@limpeza_bp.route("/occurrences/<int:order_id>", methods=["GET"])
@jwt_required()
def listar_ocorrencias(order_id):
    cid = _company_id()
    order = Order.query.filter_by(id=order_id, company_id=cid).first()
    if not order:
        return jsonify({"erro": "O.S não encontrada"}), 404
    occs = LimpezaOccurrence.query.filter_by(order_id=order_id).order_by(LimpezaOccurrence.created_at.desc()).all()
    return jsonify({"ocorrencias": [o.to_dict() for o in occs]}), 200


@limpeza_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200