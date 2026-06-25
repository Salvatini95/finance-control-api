from flask import Blueprint, request, jsonify
from app.extensions import db
from costwise.services.license_service import LicenseService
from costwise.services.email_service import EmailService
from costwise.services.webhook_service import WebhookService
from costwise.models.ping import PingEvent
from sqlalchemy import text

costwise_bp = Blueprint("costwise", __name__, url_prefix="/costwise")

_license_svc = LicenseService(db)
_email_svc   = EmailService()
_webhook_svc = WebhookService()


@costwise_bp.route("/webhook", methods=["POST"])
def webhook():
    """Recebe pagamento do Gumroad, gera chave e envia email."""
    raw_body  = request.get_data()
    signature = request.headers.get("X-Gumroad-Signature", "")

    if not _webhook_svc.verify_signature(raw_body, signature):
        return jsonify({"error": "Assinatura inválida"}), 401

    dados = _webhook_svc.parse_gumroad_payload(request.form.to_dict())

    if dados["refunded"] or dados["test"]:
        return jsonify({"ok": True, "skipped": True})

    if not dados["email"] or not dados["sale_id"]:
        return jsonify({"error": "Payload incompleto"}), 400

    plano   = _webhook_svc.determinar_plano(dados)
    license = _license_svc.generate(dados["email"], plano, dados["sale_id"])
    _email_svc.send_license(dados["email"], license)

    return jsonify({"ok": True, "key": license.key})


@costwise_bp.route("/activate", methods=["POST"])
def activate():
    """Valida chave de licença e registra ativação."""
    body = request.get_json(silent=True) or {}
    key  = str(body.get("key", "")).strip()

    if not key:
        return jsonify({"valid": False, "error": "Chave não informada"}), 400

    license = _license_svc.validate(key)
    if not license:
        return jsonify({"valid": False, "error": "Chave inválida ou expirada"}), 400

    if not license.activated_at:
        _license_svc.mark_activated(key)

    return jsonify({"valid": True, **license.to_dict()})


@costwise_bp.route("/ping", methods=["POST"])
def ping():
    """Recebe telemetria anônima e persiste no Supabase."""
    body = request.get_json(silent=True) or {}

    install_id = str(body.get("install_id", ""))[:64]
    if not install_id:
        return jsonify({"ok": False}), 400

    try:
        db.session.execute(text("""
            INSERT INTO costwise_pings
                (install_id, version, days_remaining, is_pro, platform, project_count, tokens_range)
            VALUES
                (:install_id, :version, :days_remaining, :is_pro, :platform, :project_count, :tokens_range)
        """), {
            "install_id":     install_id,
            "version":        str(body.get("version", ""))[:20],
            "days_remaining": int(body.get("days_remaining", 0) or 0),
            "is_pro":         bool(body.get("is_pro", False)),
            "platform":       str(body.get("platform", ""))[:20],
            "project_count":  int(body.get("project_count", 0) or 0),
            "tokens_range":   str(body.get("tokens_range", ""))[:20],
        })
        db.session.commit()
    except Exception as e:
        print(f"[costwise/ping] Erro: {e}")
        db.session.rollback()

    return jsonify({"ok": True})


@costwise_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "costwise"})
