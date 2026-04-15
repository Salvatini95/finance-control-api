from flask import Blueprint, jsonify
from app.email_service import send_verification_email

test_bp = Blueprint("test", __name__)

@test_bp.route("/test-email", methods=["GET"])
def test_email():
    ok = send_verification_email(
        to_email="SEU_EMAIL_REAL_AQUI",
        name="Guilherme",
        token="teste123"
    )

    return jsonify({"success": ok})
