from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.extensions import db
from app.models import User, Company
from app.email_service import send_verification_email, send_password_reset_email
from datetime import date
import secrets, os

auth_bp = Blueprint("auth", __name__)

DEV_MODE = os.environ.get("DEV_MODE", "True").lower() not in ("false", "0", "no")
APP_URL  = os.environ.get("APP_URL", "https://svfinance.com.br")

VALID_NICHOS = {
    "generic", "contador", "barbeiro", "mototaxi",
    "estetica", "restaurante", "loja", "marceneiro"
}

def _get_to_email(real_email):
    if DEV_MODE:
        return "salvatiniguilherme@gmail.com"
    return real_email


# =========================
# HEALTH CHECK
# =========================
@auth_bp.route("/health", methods=["GET"])
def health():
    """
    Rota de verificação de saúde do servidor.
    Usada pelo UptimeRobot para monitorar se o sistema está no ar.
    Não requer autenticação.
    """
    return jsonify({
        "status":  "ok",
        "service": "sv-finance-api",
        "version": "1.0.0",
    }), 200


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
    nicho        = data.get("nicho", "generic").strip().lower()

    if nicho not in VALID_NICHOS:
        nicho = "generic"

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

    verification_token = secrets.token_urlsafe(32)

    new_company = Company(
        name       = company_name,
        plan       = "free",
        nicho      = nicho,
        created_at = str(date.today()),
        active     = True,
    )
    db.session.add(new_company)
    db.session.flush()

    new_user = User(
        email                    = email,
        name                     = name,
        role                     = "admin",
        account_type             = "business",
        company_id               = new_company.id,
        active                   = True,
        email_verified           = False,
        email_verification_token = verification_token,
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    try:
        send_verification_email(
            to_email = _get_to_email(email),
            name     = name,
            token    = verification_token,
            app_url  = APP_URL,
        )
    except Exception as e:
        print(f"Erro ao enviar email de verificação (PJ): {e}")

    return jsonify({
        "msg":          "Empresa criada! Verifique seu email para ativar a conta.",
        "company_id":   new_company.id,
        "company_name": new_company.name,
        "plan":         new_company.plan,
        "nicho":        new_company.nicho,
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

    verification_token = secrets.token_urlsafe(32)

    new_user = User(
        email                    = email,
        name                     = name,
        role                     = "admin",
        account_type             = "personal",
        company_id               = None,
        active                   = True,
        email_verified           = False,
        email_verification_token = verification_token,
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    try:
        send_verification_email(
            to_email = _get_to_email(email),
            name     = name,
            token    = verification_token,
            app_url  = APP_URL,
        )
    except Exception as e:
        print(f"Erro ao enviar email de verificação (PF): {e}")

    return jsonify({
        "msg":   "Conta criada! Verifique seu email para ativar a conta.",
        "plan":  "free",
        "nicho": "generic",
    }), 201


# =========================
# VERIFICAR EMAIL
# =========================
@auth_bp.route("/verify-email", methods=["GET"])
def verify_email():
    token = request.args.get("token", "").strip()
    if not token:
        return jsonify({"msg": "Token inválido"}), 400

    user = User.query.filter_by(email_verification_token=token).first()
    if not user:
        return jsonify({"msg": "Token inválido ou já utilizado"}), 404

    user.email_verified           = True
    user.email_verification_token = None
    db.session.commit()

    return jsonify({"msg": "Email verificado com sucesso! Você já pode fazer login."}), 200


# =========================
# REENVIAR VERIFICAÇÃO
# =========================
@auth_bp.route("/resend-verification", methods=["POST"])
def resend_verification():
    data  = request.get_json()
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"msg": "Email é obrigatório"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"msg": "Email não encontrado"}), 404
    if user.email_verified:
        return jsonify({"msg": "Email já verificado"}), 400

    new_token                     = secrets.token_urlsafe(32)
    user.email_verification_token = new_token
    db.session.commit()

    try:
        send_verification_email(
            to_email = _get_to_email(email),
            name     = user.name or "Usuário",
            token    = new_token,
            app_url  = APP_URL,
        )
    except Exception as e:
        print(f"Erro ao reenviar email: {e}")

    return jsonify({"msg": "Email de verificação reenviado!"}), 200


# =========================
# AUTO-VERIFICAR (DEV ONLY)
# =========================
@auth_bp.route("/dev/verify/<email>", methods=["GET"])
def dev_verify(email):
    if not DEV_MODE:
        return jsonify({"msg": "Rota disponível apenas em DEV"}), 403

    user = User.query.filter_by(email=email.lower()).first()
    if not user:
        return jsonify({"msg": "Usuário não encontrado"}), 404

    user.email_verified           = True
    user.email_verification_token = None
    db.session.commit()

    return jsonify({"msg": f"Usuário {email} verificado com sucesso!"}), 200


# =========================
# ESQUECEU A SENHA
# =========================
@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data  = request.get_json()
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"msg": "Email é obrigatório"}), 400

    user = User.query.filter_by(email=email).first()
    if user:
        reset_token               = secrets.token_urlsafe(32)
        user.reset_password_token = reset_token
        db.session.commit()
        try:
            send_password_reset_email(
                to_email = _get_to_email(email),
                name     = user.name or "Usuário",
                token    = reset_token,
                app_url  = APP_URL,
            )
        except Exception as e:
            print(f"Erro ao enviar email de reset: {e}")

    return jsonify({"msg": "Se este email estiver cadastrado, você receberá as instruções em breve."}), 200


# =========================
# RESETAR SENHA
# =========================
@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data     = request.get_json()
    token    = data.get("token", "").strip()
    password = data.get("password", "").strip()

    if not token or not password:
        return jsonify({"msg": "Token e nova senha são obrigatórios"}), 400
    if len(password) < 6:
        return jsonify({"msg": "A senha deve ter no mínimo 6 caracteres"}), 400

    user = User.query.filter_by(reset_password_token=token).first()
    if not user:
        return jsonify({"msg": "Token inválido ou já utilizado"}), 404

    user.set_password(password)
    user.reset_password_token = None
    db.session.commit()

    return jsonify({"msg": "Senha redefinida com sucesso! Faça login com a nova senha."}), 200


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

    if not user.email_verified:
        return jsonify({
            "msg":              "Email não verificado. Verifique sua caixa de entrada.",
            "email_unverified": True,
            "email":            email,
        }), 403

    token = create_access_token(identity=str(user.id))

    return jsonify({
        "token":        token,
        "user_id":      user.id,
        "email":        user.email,
        "name":         user.name or "",
        "role":         user.role,
        "account_type": user.account_type,
        "company_id":   user.company_id,
        "company_name": user.company.name  if user.company else "",
        "plan":         user.company.plan  if user.company else "free",
        "nicho":        user.company.nicho if user.company else "generic",
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
        "id":             user.id,
        "name":           user.name,
        "email":          user.email,
        "role":           user.role,
        "account_type":   user.account_type,
        "company_id":     user.company_id,
        "company_name":   user.company.name  if user.company else "",
        "plan":           user.company.plan  if user.company else "free",
        "nicho":          user.company.nicho if user.company else "generic",
        "email_verified": user.email_verified,
    }), 200