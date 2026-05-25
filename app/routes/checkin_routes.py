# app/routes/checkin_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import User, Client, Order, ServiceCheckin
from datetime import datetime, timezone

checkin_bp = Blueprint("checkin", __name__)


def _get_user(user_id):
    return User.query.get(int(user_id))


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _diff_minutes(start_str, end_str):
    try:
        fmt   = "%Y-%m-%dT%H:%M:%S"
        start = datetime.strptime(start_str, fmt)
        end   = datetime.strptime(end_str,   fmt)
        return max(0, int((end - start).total_seconds() / 60))
    except Exception:
        return None


# ────────────────────────────────────────────────────────────
# GET /api/checkin/open   ← DEVE VIR ANTES de /checkin/<int:id>
# Verifica se o colaborador tem check-in em aberto
# ────────────────────────────────────────────────────────────
@checkin_bp.route("/checkin/open", methods=["GET"])
@jwt_required()
def get_open_checkin():
    """Verifica se o colaborador tem check-in em aberto."""
    user = _get_user(get_jwt_identity())

    checkin = ServiceCheckin.query.filter_by(
        user_id=user.id,
        company_id=user.company_id,
        type="checkin"
    ).filter(ServiceCheckin.checkout_at == None).order_by(
        ServiceCheckin.id.desc()
    ).first()

    if not checkin:
        return jsonify({"open": False}), 200

    client = Client.query.get(checkin.client_id)
    order  = Order.query.get(checkin.order_id) if checkin.order_id else None

    return jsonify({
        "open":         True,
        "checkin_id":   checkin.id,
        "checkin_at":   checkin.checkin_at,
        "client_name":  client.name if client else "",
        "order_number": order.number if order else "",
        "order_id":     checkin.order_id,
    }), 200


# ────────────────────────────────────────────────────────────
# GET /api/clients/<id>/qrcode
# ────────────────────────────────────────────────────────────
@checkin_bp.route("/clients/<int:client_id>/qrcode", methods=["GET"])
@jwt_required()
def get_client_qrcode(client_id):
    user   = _get_user(get_jwt_identity())
    client = Client.query.filter_by(id=client_id, company_id=user.company_id).first()
    if not client:
        return jsonify({"msg": "Cliente não encontrado"}), 404

    app_url     = "https://app.svfinance.com.br"
    checkin_url = f"{app_url}/checkin/{client_id}?c={user.company_id}"

    return jsonify({
        "checkin_url": checkin_url,
        "client_id":   client_id,
        "client_name": client.name,
    }), 200


# ────────────────────────────────────────────────────────────
# POST /api/checkin/<client_id>/start
# ────────────────────────────────────────────────────────────
@checkin_bp.route("/checkin/<int:client_id>/start", methods=["POST"])
@jwt_required()
def checkin_start(client_id):
    user   = _get_user(get_jwt_identity())
    data   = request.get_json() or {}
    client = Client.query.filter_by(id=client_id, company_id=user.company_id).first()
    if not client:
        return jsonify({"msg": "Cliente não encontrado"}), 404

    order_id = data.get("order_id")
    if order_id:
        order = Order.query.filter_by(id=order_id, company_id=user.company_id).first()
        if not order:
            return jsonify({"msg": "O.S não encontrada"}), 404
        if order.status == "done":
            return jsonify({"msg": "Esta O.S já foi concluída"}), 400

        existing = ServiceCheckin.query.filter_by(
            order_id=order_id,
            user_id=user.id,
            type="checkin"
        ).filter(ServiceCheckin.checkout_at == None).first()

        if existing:
            return jsonify({
                "msg":        "Você já tem um check-in aberto para esta O.S",
                "checkin_id": existing.id,
                "checkin_at": existing.checkin_at,
            }), 400

        if order.status == "open":
            order.status = "in_progress"

    now = _now()

    checkin = ServiceCheckin(
        client_id   =client_id,
        user_id     =user.id,
        company_id  =user.company_id,
        order_id    =order_id,
        executed_at =now,
        checkin_at  =now,
        checkout_at =None,
        duration_min=None,
        type        ="checkin",
        latitude    =data.get("lat"),
        longitude   =data.get("lon"),
        notes       =data.get("notes", "").strip() or None,
    )
    db.session.add(checkin)
    db.session.commit()

    return jsonify({
        "msg":         "✅ Check-in registrado!",
        "checkin_id":  checkin.id,
        "checkin_at":  checkin.checkin_at,
        "client_name": client.name,
        "order_id":    order_id,
    }), 201


# ────────────────────────────────────────────────────────────
# POST /api/checkin/<checkin_id>/finish
# ────────────────────────────────────────────────────────────
@checkin_bp.route("/checkin/<int:checkin_id>/finish", methods=["POST"])
@jwt_required()
def checkin_finish(checkin_id):
    user    = _get_user(get_jwt_identity())
    data    = request.get_json() or {}
    checkin = ServiceCheckin.query.filter_by(
        id=checkin_id,
        user_id=user.id,
        company_id=user.company_id
    ).first()

    if not checkin:
        return jsonify({"msg": "Check-in não encontrado"}), 404
    if checkin.checkout_at:
        return jsonify({"msg": "Este check-in já foi finalizado"}), 400

    now      = _now()
    duration = _diff_minutes(checkin.checkin_at, now)

    checkin.checkout_at  = now
    checkin.duration_min = duration
    if data.get("notes"):
        checkin.notes = data.get("notes")

    db.session.commit()

    h       = duration // 60 if duration else 0
    m       = duration % 60  if duration else 0
    dur_str = f"{h}h{m:02d}min" if h > 0 else f"{m}min"

    return jsonify({
        "msg":          f"✅ Check-out registrado! Duração: {dur_str}",
        "checkin_id":   checkin.id,
        "checkin_at":   checkin.checkin_at,
        "checkout_at":  checkin.checkout_at,
        "duration_min": duration,
        "duration_str": dur_str,
    }), 200


# ────────────────────────────────────────────────────────────
# GET /api/clients/<id>/checkins
# ────────────────────────────────────────────────────────────
@checkin_bp.route("/clients/<int:client_id>/checkins", methods=["GET"])
@jwt_required()
def get_client_checkins(client_id):
    user  = _get_user(get_jwt_identity())
    limit = min(int(request.args.get("limit", 50)), 200)

    checkins = (
        ServiceCheckin.query
        .filter_by(client_id=client_id, company_id=user.company_id)
        .order_by(ServiceCheckin.id.desc())
        .limit(limit)
        .all()
    )
    return jsonify([c.to_dict() for c in checkins]), 200


# ────────────────────────────────────────────────────────────
# GET /api/checkins  (ADM)
# ────────────────────────────────────────────────────────────
@checkin_bp.route("/checkins", methods=["GET"])
@jwt_required()
def get_all_checkins():
    user = _get_user(get_jwt_identity())

    if user.role not in ("admin", "financial"):
        return jsonify({"msg": "Sem permissão"}), 403

    date_from      = request.args.get("date_from")
    date_to        = request.args.get("date_to")
    filter_user_id = request.args.get("user_id", type=int)
    limit          = min(int(request.args.get("limit", 100)), 500)

    query = ServiceCheckin.query.filter_by(company_id=user.company_id)

    if filter_user_id:
        query = query.filter_by(user_id=filter_user_id)
    if date_from:
        query = query.filter(ServiceCheckin.executed_at >= date_from)
    if date_to:
        query = query.filter(ServiceCheckin.executed_at <= f"{date_to}T23:59:59")

    checkins = query.order_by(ServiceCheckin.id.desc()).limit(limit).all()
    return jsonify([c.to_dict() for c in checkins]), 200