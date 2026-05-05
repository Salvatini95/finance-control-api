from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import User, Company
from datetime import date

company_bp = Blueprint("company", __name__)

VALID_ROLES = ["admin", "seller", "financial", "stock", "viewer"]


def _get_current_user():
    user_id = int(get_jwt_identity())
    return User.query.get(user_id)


def _require_admin(user):
    if not user or user.role != "admin":
        return jsonify({"msg": "Acesso restrito a administradores"}), 403
    return None


# =========================
# DADOS DA EMPRESA
# =========================

@company_bp.route("/company", methods=["GET"])
@jwt_required()
def get_company():
    user = _get_current_user()
    if not user or not user.company_id:
        return jsonify({}), 200
    c = user.company
    return jsonify({
        # ── dados gerais ──
        "id":              c.id,
        "company_name":    c.name,
        "company_cnpj":    c.cnpj,
        "company_address": c.address,
        "company_logo":    c.logo,
        "plan":            c.plan,
        "nicho":           c.nicho,
        "created_at":      c.created_at,
        # ── campos fiscais NF-e ──
        "cnpj":                c.cnpj,
        "inscricao_estadual":  c.inscricao_estadual,
        "inscricao_municipal": c.inscricao_municipal,
        "regime_tributario":   c.regime_tributario or "1",
        "cep":                 c.cep,
        "logradouro":          c.logradouro,
        "numero":              c.numero,
        "complemento":         c.complemento,
        "bairro":              c.bairro,
        "municipio":           c.municipio,
        "uf":                  c.uf,
        "codigo_municipio":    c.codigo_municipio,
        "telefone":            c.telefone,
        "token_focusnfe":      c.token_focusnfe,
    }), 200


@company_bp.route("/company", methods=["PUT"])
@jwt_required()
def update_company():
    user = _get_current_user()
    err  = _require_admin(user)
    if err: return err

    data = request.get_json()
    c    = user.company

    # ── dados gerais ──
    c.name    = data.get("company_name",    c.name)
    c.cnpj    = data.get("company_cnpj",    c.cnpj)
    c.address = data.get("company_address", c.address)
    c.logo    = data.get("company_logo",    c.logo)

    # ── campos fiscais NF-e ──
    # cnpj pode vir tanto como "cnpj" (fiscal) quanto "company_cnpj" (empresa)
    if data.get("cnpj"):
        c.cnpj = data.get("cnpj")

    if data.get("inscricao_estadual")  is not None: c.inscricao_estadual  = data["inscricao_estadual"]
    if data.get("inscricao_municipal") is not None: c.inscricao_municipal = data["inscricao_municipal"]
    if data.get("regime_tributario")   is not None: c.regime_tributario   = data["regime_tributario"]
    if data.get("cep")                 is not None: c.cep                 = data["cep"]
    if data.get("logradouro")          is not None: c.logradouro          = data["logradouro"]
    if data.get("numero")              is not None: c.numero              = data["numero"]
    if data.get("complemento")         is not None: c.complemento         = data["complemento"]
    if data.get("bairro")              is not None: c.bairro              = data["bairro"]
    if data.get("municipio")           is not None: c.municipio           = data["municipio"]
    if data.get("uf")                  is not None: c.uf                  = data["uf"]
    if data.get("codigo_municipio")    is not None: c.codigo_municipio    = data["codigo_municipio"]
    if data.get("telefone")            is not None: c.telefone            = data["telefone"]
    if data.get("token_focusnfe")      is not None: c.token_focusnfe      = data["token_focusnfe"]

    db.session.commit()
    return jsonify({"msg": "Dados da empresa atualizados"}), 200


# =========================
# PERFIL DO USUÁRIO LOGADO
# =========================

@company_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    user = _get_current_user()
    return jsonify({
        "id":    user.id,
        "name":  user.name,
        "email": user.email,
        "role":  user.role,
    }), 200


@company_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_me():
    user = _get_current_user()
    data = request.get_json()

    name         = data.get("name", "").strip()
    old_password = data.get("old_password", "").strip()
    new_password = data.get("new_password", "").strip()

    if name:
        user.name = name

    if new_password:
        if not old_password:
            return jsonify({"msg": "Informe a senha atual"}), 400
        if not user.check_password(old_password):
            return jsonify({"msg": "Senha atual incorreta"}), 400
        if len(new_password) < 6:
            return jsonify({"msg": "Nova senha deve ter no mínimo 6 caracteres"}), 400
        user.set_password(new_password)

    db.session.commit()
    return jsonify({"msg": "Perfil atualizado com sucesso"}), 200


# =========================
# LISTAR USUÁRIOS DA EMPRESA
# =========================

@company_bp.route("/company/users", methods=["GET"])
@jwt_required()
def list_users():
    user = _get_current_user()
    err  = _require_admin(user)
    if err: return err

    users = User.query.filter_by(company_id=user.company_id).all()
    return jsonify([{
        "id":     u.id,
        "name":   u.name,
        "email":  u.email,
        "role":   u.role,
        "active": u.active,
    } for u in users]), 200


# =========================
# CRIAR USUÁRIO NA EMPRESA
# =========================

@company_bp.route("/company/users", methods=["POST"])
@jwt_required()
def create_user():
    user = _get_current_user()
    err  = _require_admin(user)
    if err: return err

    data     = request.get_json()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
    name     = data.get("name", "").strip()
    role     = data.get("role", "seller").strip()

    if not email or not password or not name:
        return jsonify({"msg": "Nome, email e senha são obrigatórios"}), 400
    if len(password) < 6:
        return jsonify({"msg": "Senha deve ter no mínimo 6 caracteres"}), 400
    if role not in VALID_ROLES:
        return jsonify({"msg": f"Role inválida. Use: {VALID_ROLES}"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email já cadastrado"}), 409

    company    = user.company
    user_count = User.query.filter_by(company_id=company.id).count()
    if company.plan == "free" and user_count >= 10:
        return jsonify({"msg": "Limite de usuários atingido. Faça upgrade para Pro."}), 403

    new_user = User(
        email      = email,
        name       = name,
        role       = role,
        company_id = user.company_id,
        active     = True,
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "Usuário criado com sucesso", "id": new_user.id, "role": new_user.role}), 201


# =========================
# ATUALIZAR USUÁRIO
# =========================

@company_bp.route("/company/users/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_user(user_id):
    admin = _get_current_user()
    err   = _require_admin(admin)
    if err: return err

    target = User.query.filter_by(id=user_id, company_id=admin.company_id).first()
    if not target:
        return jsonify({"msg": "Usuário não encontrado"}), 404

    data = request.get_json()
    role = data.get("role", target.role)

    if role not in VALID_ROLES:
        return jsonify({"msg": f"Role inválida. Use: {VALID_ROLES}"}), 400
    if target.id == admin.id and role != "admin":
        return jsonify({"msg": "Você não pode alterar sua própria role"}), 400

    target.name   = data.get("name",   target.name)
    target.role   = role
    target.active = data.get("active", target.active)

    new_password = data.get("password", "").strip()
    if new_password:
        if len(new_password) < 6:
            return jsonify({"msg": "Senha deve ter no mínimo 6 caracteres"}), 400
        target.set_password(new_password)

    db.session.commit()
    return jsonify({"msg": "Usuário atualizado"}), 200


# =========================
# REMOVER USUÁRIO
# =========================

@company_bp.route("/company/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    admin = _get_current_user()
    err   = _require_admin(admin)
    if err: return err

    if admin.id == user_id:
        return jsonify({"msg": "Você não pode remover a si mesmo"}), 400

    target = User.query.filter_by(id=user_id, company_id=admin.company_id).first()
    if not target:
        return jsonify({"msg": "Usuário não encontrado"}), 404

    target.active = False
    db.session.commit()
    return jsonify({"msg": "Usuário desativado com sucesso"}), 200