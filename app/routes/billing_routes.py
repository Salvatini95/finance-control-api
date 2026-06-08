"""
Rotas de cobrança SaaS — apenas HTTP.
Toda lógica de negócio está em AsaasService.

Endpoints:
  POST /api/billing/trial          → inicia trial de 7 dias (sem cartão)
  POST /api/billing/subscribe      → assina plano Pro ou Business
  GET  /api/billing/status         → retorna status da assinatura atual
  POST /api/billing/cancel         → cancela assinatura ativa
  POST /api/billing/webhook        → recebe eventos do Asaas (sem JWT)
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User
from app.services.asaas_service import AsaasService

billing_bp = Blueprint("billing", __name__, url_prefix="/api/billing")


def _get_user(user_id: str) -> User:
    return User.query.get(int(user_id))


# ── Trial ─────────────────────────────────────────────────────────────────────

@billing_bp.route("/trial", methods=["POST"])
@jwt_required()
def iniciar_trial():
    """Inicia trial de 7 dias sem cartão para a empresa do usuário logado."""
    user    = _get_user(get_jwt_identity())
    company = user.company

    if not company:
        return jsonify({"ok": False, "msg": "Empresa não encontrada."}), 404

    result = AsaasService.iniciar_trial(company=company)
    code   = result.pop("code", 200)
    return jsonify(result), code


# ── Assinatura ────────────────────────────────────────────────────────────────

@billing_bp.route("/subscribe", methods=["POST"])
@jwt_required()
def criar_assinatura():
    """
    Cria assinatura recorrente no Asaas.

    Body esperado:
    {
      "plan":         "pro" | "business",
      "interval":     "monthly" | "yearly",
      "billing_type": "PIX" | "CREDIT_CARD",
      "titular": {
        "name":          "João Silva",
        "cpfCnpj":       "12345678901",
        "email":         "joao@email.com",
        "phone":         "44999999999",
        "postalCode":    "87010000",
        "addressNumber": "123"
      },
      "credit_card": {             ← apenas se billing_type = CREDIT_CARD
        "holderName":  "JOAO SILVA",
        "number":      "4111111111111111",
        "expiryMonth": "05",
        "expiryYear":  "2028",
        "ccv":         "123"
      }
    }
    """
    user    = _get_user(get_jwt_identity())
    company = user.company

    if not company:
        return jsonify({"ok": False, "msg": "Empresa não encontrada."}), 404

    if not user.is_admin:
        return jsonify({"ok": False, "msg": "Apenas administradores podem assinar planos."}), 403

    data   = request.get_json() or {}
    result = AsaasService.criar_assinatura(company=company, dados=data)
    code   = result.pop("code", 200)
    return jsonify(result), code


# ── Status ────────────────────────────────────────────────────────────────────

@billing_bp.route("/status", methods=["GET"])
@jwt_required()
def status_assinatura():
    """Retorna status da assinatura atual da empresa do usuário logado."""
    user    = _get_user(get_jwt_identity())
    company = user.company

    if not company:
        return jsonify({"ok": False, "msg": "Empresa não encontrada."}), 404

    result = AsaasService.status_assinatura(company=company)
    code   = result.pop("code", 200)
    return jsonify(result), code


# ── Cancelamento ──────────────────────────────────────────────────────────────

@billing_bp.route("/cancel", methods=["POST"])
@jwt_required()
def cancelar_assinatura():
    """Cancela assinatura ativa da empresa. Apenas admin pode cancelar."""
    user    = _get_user(get_jwt_identity())
    company = user.company

    if not company:
        return jsonify({"ok": False, "msg": "Empresa não encontrada."}), 404

    if not user.is_admin:
        return jsonify({"ok": False, "msg": "Apenas administradores podem cancelar."}), 403

    result = AsaasService.cancelar_assinatura(company=company)
    code   = result.pop("code", 200)
    return jsonify(result), code


# ── Webhook Asaas (sem JWT — chamado pelo servidor do Asaas) ──────────────────

@billing_bp.route("/webhook", methods=["POST"])
def webhook_asaas():
    """
    Recebe eventos de pagamento enviados pelo Asaas.

    Não usa JWT — o Asaas chama este endpoint diretamente.
    Configurar no painel Asaas:
      URL: https://api.svfinance.com.br/api/billing/webhook

    Eventos tratados:
      PAYMENT_CONFIRMED / PAYMENT_RECEIVED → ativa assinatura
      PAYMENT_OVERDUE                       → marca inadimplência
      PAYMENT_DELETED / PAYMENT_REFUNDED    → cancela
      SUBSCRIPTION_DELETED                  → cancela
    """
    payload = request.get_json(silent=True) or {}
    evento  = payload.get("event", "")

    result = AsaasService.processar_webhook(evento=evento, payload=payload)
    code   = result.pop("code", 200)
    return jsonify(result), code