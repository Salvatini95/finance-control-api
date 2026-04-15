from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.extensions import db
from app.models import User, Company
from datetime import date

# 🔽 NOVOS IMPORTS
import secrets
from app.email_service import send_verification_email

auth_bp = Blueprint("auth", __name__)


# =========================
# REGISTRO EMPRESA (PJ)
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

    # 🔐 gera token
    token = secrets.token_urlsafe(32)

    new_company = Company(
        name       = company_name,
        plan       = "free",
        created_at = str(date.today()),
        active     = True,
    )
    db.session.add(new_company)
    db.session.flush()

    new_user = User(
        email        = email,
        name         = name,
        role         = "admin",
        account_type = "business",
        company_id   = new_company.id,
        active       = True,
        # ⚠️ ainda não usamos no banco (próximo passo)
    )
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    # 📩 envio de email (não quebra nada se falhar)
    try:
        send_verification_email(
            to_email=email,
            name=name,
            token=token
        )
    except Exception as e:
        print(f"Erro ao enviar email: {e}")

    return jsonify({
        "msg":          "Empresa e usuário criados com sucesso",
        "company_id":   new_company.id,
        "company_name": new_company.name,
        "plan":         new_company.plan,
    }), 201


# =========================
# REGISTRO PESSOAL (PF)
# =========================
@auth_bp.route("/register/personal", methods=["POST"])
def register_personal():
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Nenhum dado enviado"}), 400

    email    = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
    name     = data.get("name", "").strip()

    if not email or not password:
        return jsonify({"msg": "Email e senha são obrigatórios"}), 400
    if not name:
        return jsonify({"msg": "Nome é obrigatório"}), 400
    if len(password) < 6:
        return jsonify({"msg": "A senha deve ter no mínimo 6 caracteres"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Este email já está cadastrado"}), 409

    # 🔐 gera token
    token = secrets.token_urlsafe(32)

    new_user = User(
        email        = email,
        name         = name,
        role         = "admin",
        account_type = "personal",
        company_id   = None,
        active       = True,
    )
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    # 📩 envio de email
    try:
        send_verification_email(
            to_email=email,
            name=name,
            token=token
        )
    except Exception as e:
        print(f"Erro ao enviar email: {e}")

    return jsonify({
        "msg":  "Conta pessoal criada com sucesso",
        "plan": "free",
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

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "token":        token,
        "user_id":      user.id,
        "email":        user.email,
        "name":         user.name or "",
        "role":         user.role,
        "account_type": user.account_type,
        "company_id":   user.company_id,
        "company_name": user.company.name if user.company else "",
        "plan":         user.company.plan if user.company else "free",
    }), 200


# =========================
# PERFIL
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
        "account_type": user.account_type,
        "company_id":   user.company_id,
        "company_name": user.company.name if user.company else "",
        "plan":         user.company.plan if user.company else "free",
    }), 200
