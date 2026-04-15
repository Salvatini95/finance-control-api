from flask import Blueprint, jsonify
from app.email_service import send_verification_email

dev_bp = Blueprint("dev", __name__)

@dev_bp.route("/dev/test-email", methods=["GET"])
def test_email():
    ok = send_verification_email(
        to_email="salvatiniguilherme@gmail.com",
        name="Guilherme",
        token="teste123"
    )

    return jsonify({"success": ok})
