# app/routes/checkin_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, Client, ServiceCheckin
from app.services.checkin_service import CheckinService, _raio_metros
from app.services.pin_service import PinService

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
    user   = _get_user(get_jwt_identity())
    data   = request.get_json() or {}
    result = CheckinService.registrar_entrada(
        user=user,
        client_id=client_id,
        order_id=data.get("order_id"),
        lat=data.get("lat"),
        lon=data.get("lon"),
        notes=data.get("notes"),
        qr_token=data.get("qr_token"),
        pin=data.get("pin"),
        local_id=data.get("local_id"),
    )
    code = result.pop("code", 200)
    return jsonify(result), code


# ── POST /api/checkin/<checkin_id>/finish ────────────────────────────────────
@checkin_bp.route("/checkin/<int:checkin_id>/finish", methods=["POST"])
@jwt_required()
def checkin_finish(checkin_id):
    user   = _get_user(get_jwt_identity())
    data   = request.get_json() or {}
    result = CheckinService.registrar_saida(
        user=user,
        checkin_id=checkin_id,
        lat=data.get("lat"),
        lon=data.get("lon"),
        notes=data.get("notes"),
        qr_token=data.get("qr_token"),
        pin=data.get("pin"),
        local_id=data.get("local_id"),
    )
    code = result.pop("code", 200)
    return jsonify(result), code


# ── POST /api/checkin/pin/validate ────────────────────────────────────────────
@checkin_bp.route("/checkin/pin/validate", methods=["POST"])
@jwt_required()
def validar_pin():
    """
    Valida PIN digitado pelo colaborador.
    Aceita PIN permanente (4 dígitos) ou PIN temporário (6 dígitos).

    Body: { client_id, pin }
    Returns: { ok, tipo, pin_id }
    """
    user   = _get_user(get_jwt_identity())
    data   = request.get_json() or {}
    result = PinService.validar(
        user=user,
        client_id=data.get("client_id"),
        pin=data.get("pin", ""),
    )
    code = result.pop("code", 200)
    return jsonify(result), code


# ── POST /api/checkin/pin/generate (admin/encarregado) ───────────────────────
@checkin_bp.route("/checkin/pin/generate", methods=["POST"])
@jwt_required()
def gerar_pin():
    user   = _get_user(get_jwt_identity())
    data   = request.get_json() or {}
    result = PinService.gerar(user=user, client_id=data.get("client_id"))
    code   = result.pop("code", 200)
    return jsonify(result), code


# ── GET /api/checkin/pin/active (admin/encarregado) ──────────────────────────
@checkin_bp.route("/checkin/pin/active", methods=["GET"])
@jwt_required()
def listar_pins_ativos():
    user   = _get_user(get_jwt_identity())
    result = PinService.listar_ativos(user=user)
    code   = result.pop("code", 200)
    return jsonify(result), code


# ── POST /api/checkin/cliente/<client_id>/salvar-localizacao (só admin) ──────
@checkin_bp.route("/checkin/cliente/<int:client_id>/salvar-localizacao", methods=["POST"])
@jwt_required()
def salvar_localizacao_cliente(client_id):
    """
    Salva o GPS como localização oficial do cliente.
    RESTRITO a administradores.

    Deve ser chamado pelo admin ao colar o adesivo QR no local do cliente.
    O GPS capturado neste momento vira o ponto de referência para validação
    de check-in dos colaboradores (raio 25m).

    Body: { lat, lon }
    Returns: { ok, msg, lat, lon }
    """
    user   = _get_user(get_jwt_identity())
    data   = request.get_json() or {}
    result = CheckinService.salvar_localizacao_cliente(
        user=user,
        client_id=client_id,
        lat=data.get("lat"),
        lon=data.get("lon"),
    )
    code = result.pop("code", 200)
    return jsonify(result), code


# ── POST /api/checkin/sync (offline em lote) ─────────────────────────────────
@checkin_bp.route("/checkin/sync", methods=["POST"])
@jwt_required()
def sincronizar():
    user    = _get_user(get_jwt_identity())
    data    = request.get_json() or {}
    eventos = data.get("eventos", [])
    result  = CheckinService.sincronizar_lote(user=user, eventos=eventos)
    code    = result.pop("code", 200)
    return jsonify(result), code


# ── GET /api/orders/<order_id>/checkins ──────────────────────────────────────
@checkin_bp.route("/orders/<int:order_id>/checkins", methods=["GET"])
@jwt_required()
def get_order_checkins(order_id):
    user     = _get_user(get_jwt_identity())
    checkins = CheckinService.buscar_checkins_da_os(order_id, user.company_id)
    return jsonify(checkins), 200


# ── GET /api/clients/<id>/qrcode ─────────────────────────────────────────────
@checkin_bp.route("/clients/<int:client_id>/qrcode", methods=["GET"])
@jwt_required()
def get_client_qrcode(client_id):
    """
    Retorna dados do QR code do cliente.
    Inclui pin_cliente para impressão no adesivo e
    tem_gps para o admin saber se precisa salvar localização.
    """
    user   = _get_user(get_jwt_identity())
    client = Client.query.filter_by(id=client_id, company_id=user.company_id).first()
    if not client:
        return jsonify({"msg": "Cliente não encontrado"}), 404
    return jsonify({
        "qr_token":    CheckinService.gerar_url_qr_universal(),
        "client_id":   client_id,
        "client_name": client.name,
        "pin_cliente": client.pin_cliente,
        "raio_metros": _raio_metros(),
        "tem_gps":     client.latitude is not None and client.longitude is not None,
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
    if user.role not in ("admin", "financial", "encarregado"):
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
