# app/routes/checkin_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, Client, ServiceCheckin
from app.services.checkin_service import CheckinService

checkin_bp = Blueprint("checkin", __name__)

def _get_user(user_id):
    return User.query.get(int(user_id))

# ── GET /api/checkin/open ─────────────────────────────────────────────────────
@checkin_bp.route("/checkin/open", methods=["GET"])
@jwt_required()
def get_open_checkin():
    user   = _get_user(get_jwt_identity())
    result = CheckinService.buscar_checkin_aberto(user)
    return jsonify(result), 200

# ── GET /api/checkin/qr-token ─────────────────────────────────────────────────
@checkin_bp.route("/checkin/qr-token", methods=["GET"])
@jwt_required()
def get_qr_token():
    user = _get_user(get_jwt_identity())
    if not user.is_admin:
        return jsonify({"msg": "Sem permissão"}), 403
    return jsonify({"qr_token": CheckinService.gerar_url_qr_universal()}), 200

# ── POST /api/checkin/<client_id>/start ──────────────────────────────────────
@checkin_bp.route("/checkin/<int:client_id>/start", methods=["POST"])
@jwt_required()
def checkin_start(client_id):
    user = _get_user(get_jwt_identity())
    data = request.get_json() or {}
    result = CheckinService.registrar_entrada(
        user=user, client_id=client_id,
        order_id=data.get("order_id"),
        lat=data.get("lat"), lon=data.get("lon"),
        notes=data.get("notes"), qr_token=data.get("qr_token"),
    )
    code = result.pop("code", 200)
    return jsonify(result), code

# ── POST /api/checkin/<checkin_id>/finish ────────────────────────────────────
@checkin_bp.route("/checkin/<int:checkin_id>/finish", methods=["POST"])
@jwt_required()
def checkin_finish(checkin_id):
    user = _get_user(get_jwt_identity())
    data = request.get_json() or {}
    result = CheckinService.registrar_saida(
        user=user, checkin_id=checkin_id,
        lat=data.get("lat"), lon=data.get("lon"),
        notes=data.get("notes"), qr_token=data.get("qr_token"),
    )
    code = result.pop("code", 200)
    return jsonify(result), code

# ── GET /api/orders/<order_id>/checkins ──────────────────────────────────────
@checkin_bp.route("/orders/<int:order_id>/checkins", methods=["GET"])
@jwt_required()
def get_order_checkins(order_id):
    """Retorna todos os checkins de uma OS — para o modal de detalhes."""
    user = _get_user(get_jwt_identity())
    checkins = CheckinService.buscar_checkins_da_os(order_id, user.company_id)
    return jsonify(checkins), 200

# ── GET /api/clients/<id>/qrcode ─────────────────────────────────────────────
@checkin_bp.route("/clients/<int:client_id>/qrcode", methods=["GET"])
@jwt_required()
def get_client_qrcode(client_id):
    user   = _get_user(get_jwt_identity())
    client = Client.query.filter_by(id=client_id, company_id=user.company_id).first()
    if not client:
        return jsonify({"msg": "Cliente não encontrado"}), 404
    return jsonify({
        "qr_token":    CheckinService.gerar_url_qr_universal(),
        "client_id":   client_id,
        "client_name": client.name,
        "raio_metros": RAIO_MAXIMO_METROS if hasattr(CheckinService, 'RAIO_MAXIMO_METROS') else 300,
    }), 200

# ── GET /api/clients/<id>/checkins ───────────────────────────────────────────
@checkin_bp.route("/clients/<int:client_id>/checkins", methods=["GET"])
@jwt_required()
def get_client_checkins(client_id):
    user  = _get_user(get_jwt_identity())
    limit = min(int(request.args.get("limit", 50)), 200)
    checkins = (
        ServiceCheckin.query
        .filter_by(client_id=client_id, company_id=user.company_id)
        .order_by(ServiceCheckin.id.desc())
        .limit(limit).all()
    )
    return jsonify([c.to_dict() for c in checkins]), 200

# ── GET /api/checkins (ADM) ──────────────────────────────────────────────────
@checkin_bp.route("/checkins", methods=["GET"])
@jwt_required()
def get_all_checkins():
    user = _get_user(get_jwt_identity())
    if user.role not in ("admin", "financial"):
        return jsonify({"msg": "Sem permissão"}), 403
    date_from      = request.args.get("date_from")
    date_to        = request.args.get("date_to")
    filter_user_id = request.args.get("user_id", type=int)
    limit          = min(int(request.args.get("limit", 100)), 500)
    query = ServiceCheckin.query.filter_by(company_id=user.company_id)
    if filter_user_id:
        query = query.filter_by(user_id=filter_user_id)
    if date_from:
        query = query.filter(ServiceCheckin.executed_at >= date_from)
    if date_to:
        query = query.filter(ServiceCheckin.executed_at <= f"{date_to}T23:59:59")
    checkins = query.order_by(ServiceCheckin.id.desc()).limit(limit).all()
    return jsonify([c.to_dict() for c in checkins]), 200