from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Goal
from datetime import date

goal_bp = Blueprint("goals", __name__)


def _get_user():
    from app.models import User
    return User.query.get(int(get_jwt_identity()))


def _find_goal(id, user):
    if user.company_id:
        return Goal.query.filter_by(id=id, company_id=user.company_id).first()
    return Goal.query.filter_by(id=id, user_id=user.id).first()


def _serialize(g):
    return {
        "id":          g.id,
        "name":        g.name,
        "description": g.description,
        "target":      g.target,
        "current":     g.current,
        "progress":    g.progress,
        "remaining":   g.remaining,
        "category":    g.category,
        "icon":        g.icon,
        "deadline":    g.deadline,
        "status":      g.status,
        "created_at":  g.created_at,
    }


# ── GET /goals ──
@goal_bp.route("/goals", methods=["GET"])
@jwt_required()
def list_goals():
    user = _get_user()
    if not user: return jsonify({"msg": "Usuário não encontrado"}), 404

    if user.company_id:
        goals = Goal.query.filter_by(company_id=user.company_id).order_by(Goal.id.desc()).all()
    else:
        goals = Goal.query.filter_by(user_id=user.id).order_by(Goal.id.desc()).all()

    return jsonify([_serialize(g) for g in goals]), 200


# ── POST /goals ──
@goal_bp.route("/goals", methods=["POST"])
@jwt_required()
def create_goal():
    user = _get_user()
    if not user: return jsonify({"msg": "Usuário não encontrado"}), 404

    data = request.get_json()
    if not data: return jsonify({"msg": "Nenhum dado enviado"}), 400

    name   = data.get("name", "").strip()
    target = data.get("target")
    if not name:   return jsonify({"msg": "Nome é obrigatório"}), 400
    if not target: return jsonify({"msg": "Valor alvo é obrigatório"}), 400

    g = Goal(
        name        = name,
        description = data.get("description", ""),
        target      = float(target),
        current     = float(data.get("current", 0)),
        category    = data.get("category", ""),
        icon        = data.get("icon", "🎯"),
        deadline    = data.get("deadline"),
        status      = "active",
        created_at  = str(date.today()),
        user_id     = user.id,
        company_id  = user.company_id,
    )
    db.session.add(g)
    db.session.commit()
    return jsonify(_serialize(g)), 201


# ── PUT /goals/<id> ──
@goal_bp.route("/goals/<int:id>", methods=["PUT"])
@jwt_required()
def update_goal(id):
    user = _get_user()
    g    = _find_goal(id, user)
    if not g: return jsonify({"msg": "Meta não encontrada"}), 404

    data = request.get_json()
    if not data: return jsonify({"msg": "Nenhum dado enviado"}), 400

    g.name        = data.get("name",        g.name)
    g.description = data.get("description", g.description)
    g.target      = float(data.get("target",  g.target))
    g.current     = float(data.get("current", g.current))
    g.category    = data.get("category",    g.category)
    g.icon        = data.get("icon",        g.icon)
    g.deadline    = data.get("deadline",    g.deadline)
    g.status      = data.get("status",      g.status)

    # auto-completa se atingiu o alvo
    if g.current >= g.target:
        g.status = "completed"

    db.session.commit()
    return jsonify(_serialize(g)), 200


# ── PATCH /goals/<id>/deposit ── adicionar valor ao progresso
@goal_bp.route("/goals/<int:id>/deposit", methods=["PATCH"])
@jwt_required()
def deposit_goal(id):
    user = _get_user()
    g    = _find_goal(id, user)
    if not g: return jsonify({"msg": "Meta não encontrada"}), 404

    data   = request.get_json()
    amount = float(data.get("amount", 0))
    if amount <= 0: return jsonify({"msg": "Valor deve ser positivo"}), 400

    g.current += amount
    if g.current >= g.target:
        g.status = "completed"

    db.session.commit()
    return jsonify(_serialize(g)), 200


# ── DELETE /goals/<id> ──
@goal_bp.route("/goals/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_goal(id):
    user = _get_user()
    g    = _find_goal(id, user)
    if not g: return jsonify({"msg": "Meta não encontrada"}), 404

    db.session.delete(g)
    db.session.commit()
    return jsonify({"msg": "Meta removida"}), 200