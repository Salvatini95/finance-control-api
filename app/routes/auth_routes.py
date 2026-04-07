from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.extensions import db
from app.models import User, Company
from datetime import date

auth_bp = Blueprint("auth", __name__)


# =========================
# REGISTRAR EMPRESA + ADMIN
# =========================

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data:
        return jsonify({"msg": "Nenhum dado enviado"}), 400

    email        = data.get("email", "").strip().lower()
    password     = data.get("password", "").strip()
    name         = data.get("name", "").strip()
    company_name = data.get("company_name", "").strip()

    if not email or not password:
        return jsonify({"msg": "Email e senha são obrigatórios"}), 400
    if not name:
        return jsonify({"msg": "Nome é obrigatório"}), 400
    if not company_name:
        return jsonify({"msg": "Nome da empresa é obrigatório"}), 400
    if len(password) < 6:
        return jsonify({"msg": "A senha deve ter no mínimo 6 caracteres"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Este email já está cadastrado"}), 409

    # 1. Cria a empresa
    new_company = Company(
        name       = company_name,
        plan       = "free",
        created_at = str(date.today()),
        active     = True,
    )
    db.session.add(new_company)
    db.session.flush()  # gera o ID da empresa antes do commit

    # 2. Cria o usuário admin vinculado à empresa
    new_user = User(
        email      = email,
        name       = name,
        role       = "admin",
        company_id = new_company.id,
        active     = True,
    )
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "msg":          "Empresa e usuário criados com sucesso",
        "company_id":   new_company.id,
        "company_name": new_company.name,
        "plan":         new_company.plan,
    }), 201


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

    if not user or not user.check_password(password):
        return jsonify({"msg": "Email ou senha inválidos"}), 401

    if not user.active:
        return jsonify({"msg": "Usuário inativo. Contate o administrador."}), 403

    # token carrega user_id — company_id e role ficam no banco
    token = create_access_token(identity=str(user.id))

    return jsonify({
        "token":        token,
        "email":        user.email,
        "name":         user.name or "",
        "role":         user.role,
        "company_id":   user.company_id,
        "company_name": user.company.name if user.company else "",
        "plan":         user.company.plan if user.company else "free",
    }), 200


# =========================
# PERFIL DO USUÁRIO LOGADO
# =========================

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user    = User.query.get(user_id)

    if not user:
        return jsonify({"msg": "Usuário não encontrado"}), 404

    return jsonify({
        "id":           user.id,
        "name":         user.name,
        "email":        user.email,
        "role":         user.role,
        "company_id":   user.company_id,
        "company_name": user.company.name if user.company else "",
        "plan":         user.company.plan if user.company else "free",
    }), 200