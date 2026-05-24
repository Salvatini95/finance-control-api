# app/routes/checkin_routes.py
# ─────────────────────────────────────────────────────────────
# Rotas HTTP para QR Code e Checkin de serviço.
# Sem lógica de negócio aqui — tudo delega para QRCodeService.
# ─────────────────────────────────────────────────────────────

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.qrcode_service import QRCodeService
from app.models import User

checkin_bp = Blueprint("checkin", __name__)


def _get_company_id(user_id: int) -> int:
    """Retorna o company_id do usuário autenticado."""
    user = User.query.get(user_id)
    return user.company_id if user else None


# ────────────────────────────────────────────────────────────
# GET /api/clients/<id>/qrcode
# Gera e retorna o QR Code mestre do cliente em base64.
# Apenas admin pode gerar.
# ────────────────────────────────────────────────────────────
@checkin_bp.route("/clients/<int:client_id>/qrcode", methods=["GET"])
@jwt_required()
def get_client_qrcode(client_id: int):
    """
    Retorna o QR Code mestre do cliente.

    O QR Code é gerado dinamicamente — sempre o mesmo para
    aquele client_id. Não é armazenado no banco.

    Response:
        200: { qr_base64, checkin_url, client_id }
        403: usuário sem permissão
        400: erro na geração
    """
    user_id    = int(get_jwt_identity())
    company_id = _get_company_id(user_id)

    user = User.query.get(user_id)
    if not user or user.role not in ("admin", "financial"):
        return jsonify({"msg": "Apenas administradores podem gerar QR Codes"}), 403

    try:
        result = QRCodeService.generate_master_qr(client_id, company_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"msg": f"Erro ao gerar QR Code: {str(e)}"}), 400


# ────────────────────────────────────────────────────────────
# POST /api/checkin/<client_id>
# Registra a execução do serviço via scan do QR Code.
# Qualquer colaborador autenticado pode fazer checkin.
# ────────────────────────────────────────────────────────────
@checkin_bp.route("/checkin/<int:client_id>", methods=["POST"])
@jwt_required()
def register_checkin(client_id: int):
    """
    Registra checkin de serviço executado.

    Chamado pelo PWA quando o colaborador confirma o serviço
    após escanear o QR Code.

    Body (JSON, todos opcionais):
        lat   (float): latitude GPS
        lon   (float): longitude GPS
        notes (str):   observação do colaborador

    Response:
        201: dados do checkin criado
        400: cliente não encontrado ou erro
    """
    user_id    = int(get_jwt_identity())
    company_id = _get_company_id(user_id)
    data       = request.get_json() or {}

    lat   = data.get("lat")
    lon   = data.get("lon")
    notes = data.get("notes", "").strip() or None

    try:
        result = QRCodeService.register_checkin(
            client_id  = client_id,
            user_id    = user_id,
            company_id = company_id,
            lat        = lat,
            lon        = lon,
            notes      = notes,
        )
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        return jsonify({"msg": f"Erro ao registrar checkin: {str(e)}"}), 500


# ────────────────────────────────────────────────────────────
# GET /api/clients/<id>/checkins
# Histórico de checkins de um cliente específico.
# Admin e financial podem ver.
# ────────────────────────────────────────────────────────────
@checkin_bp.route("/clients/<int:client_id>/checkins", methods=["GET"])
@jwt_required()
def get_client_checkins(client_id: int):
    """
    Retorna o histórico de execuções de serviço de um cliente.

    Query params:
        limit (int): máximo de registros, padrão 50

    Response:
        200: lista de checkins ordenados por data desc
    """
    user_id    = int(get_jwt_identity())
    company_id = _get_company_id(user_id)
    limit      = min(int(request.args.get("limit", 50)), 200)

    user = User.query.get(user_id)
    if not user or user.role not in ("admin", "financial", "seller"):
        return jsonify({"msg": "Sem permissão"}), 403

    try:
        checkins = QRCodeService.get_client_history(client_id, company_id, limit)
        return jsonify(checkins), 200
    except Exception as e:
        return jsonify({"msg": str(e)}), 400


# ────────────────────────────────────────────────────────────
# GET /api/checkins
# Todos os checkins da empresa — visão do ADM.
# Suporta filtros de data e colaborador.
# ────────────────────────────────────────────────────────────
@checkin_bp.route("/checkins", methods=["GET"])
@jwt_required()
def get_all_checkins():
    """
    Retorna checkins da empresa com filtros opcionais.
    Usado pelo ADM para monitorar a operação do dia.

    Query params:
        date_from (str): "YYYY-MM-DD"
        date_to   (str): "YYYY-MM-DD"
        user_id   (int): filtrar por colaborador
        limit     (int): padrão 100

    Response:
        200: lista de checkins
        403: sem permissão
    """
    user_id    = int(get_jwt_identity())
    company_id = _get_company_id(user_id)

    user = User.query.get(user_id)
    if not user or user.role not in ("admin", "financial"):
        return jsonify({"msg": "Apenas administradores podem ver todos os checkins"}), 403

    date_from      = request.args.get("date_from")
    date_to        = request.args.get("date_to")
    filter_user_id = request.args.get("user_id", type=int)
    limit          = min(int(request.args.get("limit", 100)), 500)

    try:
        checkins = QRCodeService.get_company_history(
            company_id = company_id,
            date_from  = date_from,
            date_to    = date_to,
            user_id    = filter_user_id,
            limit      = limit,
        )
        return jsonify(checkins), 200
    except Exception as e:
        return jsonify({"msg": str(e)}), 500