# app/routes/nfse_routes.py
# Blueprint de emissão de NFS-e via Focus NF-e
# Registrar em app/__init__.py:
#   from app.routes.nfse_routes import nfse_bp
#   app.register_blueprint(nfse_bp)

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.nfse_service import NfseService

nfse_bp = Blueprint("nfse", __name__, url_prefix="/api/nfse")


def _get_company_id():
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        return identity.get("company_id")
    try:
        return int(identity)
    except (TypeError, ValueError):
        return None


# ── POST /api/nfse/emitir/<order_id> ────────────────────────────────────────
# Emite NFS-e para uma O.S. Deve estar com status "done" (concluída).
@nfse_bp.route("/emitir/<int:order_id>", methods=["POST"])
@jwt_required()
def emitir(order_id):
    company_id = _get_company_id()
    if not company_id:
        return jsonify({"msg": "Empresa não identificada."}), 401

    result = NfseService.emitir(order_id, company_id)
    return jsonify(result), result["code"]


# ── GET /api/nfse/consultar/<order_id> ──────────────────────────────────────
# Consulta o status de uma NFS-e já enviada (polling).
# Usar quando o status for "processando" e quiser checar se autorizou.
@nfse_bp.route("/consultar/<int:order_id>", methods=["GET"])
@jwt_required()
def consultar(order_id):
    company_id = _get_company_id()
    if not company_id:
        return jsonify({"msg": "Empresa não identificada."}), 401

    result = NfseService.consultar(order_id, company_id)
    return jsonify(result), result["code"]


# ── GET /api/nfse/status/<order_id> ─────────────────────────────────────────
# Retorna o status salvo no banco (sem chamar o Focus).
# Rápido — usar para exibir o badge na tela da O.S.
@nfse_bp.route("/status/<int:order_id>", methods=["GET"])
@jwt_required()
def status(order_id):
    from app.models import Order
    company_id = _get_company_id()
    if not company_id:
        return jsonify({"msg": "Empresa não identificada."}), 401

    order = Order.query.filter_by(id=order_id, company_id=company_id).first()
    if not order:
        return jsonify({"msg": "O.S não encontrada."}), 404

    return jsonify({
        "ok":         True,
        "order_id":   order.id,
        "nfe_status": order.nfe_status,
        "nfe_numero": order.nfe_numero,
        "nfe_chave":  order.nfe_chave,
        "nfe_ref":    getattr(order, "nfe_ref", None),
    }), 200