from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app.extensions import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


# =========================
# REGISTRAR USUÁRIO
# =========================

@auth_bp.route("/register", methods=["POST"])
def register():

    data = request.get_json()

    if not data:
        return jsonify({"msg": "Nenhum dado enviado"}), 400

    email    = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
    name     = data.get("name", "").strip()

    # --- Validações ---
    if not email or not password:
        return jsonify({"msg": "Email e senha são obrigatórios"}), 400

    if len(password) < 6:
        return jsonify({"msg": "A senha deve ter no mínimo 6 caracteres"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Este email já está cadastrado"}), 409

    # --- Criação do usuário ---
    new_user = User(email=email)
    new_user.set_password(password)   # hash seguro via werkzeug

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "Usuário criado com sucesso"}), 201


# =========================
# LOGIN
# =========================

@auth_bp.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    if not data:
        return jsonify({"msg": "Nenhum dado enviado"}), 400

    email    = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"msg": "Email e senha são obrigatórios"}), 400

    user = User.query.filter_by(email=email).first()

    # Mensagem genérica para não revelar se o email existe
    if not user or not user.check_password(password):
        return jsonify({"msg": "Email ou senha inválidos"}), 401

    token = create_access_token(identity=str(user.id))

    return jsonify({"token": token, "email": user.email}), 200