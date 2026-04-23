"""
commission_routes.py — Comissões por vendedor no SV Finance

Funcionalidades:
  - CRUD de regras de comissão por usuário (%, lucro%, valor fixo)
  - Relatório detalhado: por venda, por vendedor, por período
  - Reatribuição de vendedor em Orders (admin only)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import User, Order, CommissionRule
from datetime import datetime
import json

commission_bp = Blueprint("commission", __name__)

def _get_user(uid): return User.query.get(int(uid))
def _parse_date(v):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try: return datetime.strptime(v.strip(), fmt).date()
        except: continue
    return None

# ─────────────────────────────────────────────────────────────────────────────
# REGRAS DE COMISSÃO — CRUD
# ─────────────────────────────────────────────────────────────────────────────

@commission_bp.route("/commissions/rules", methods=["GET"])
@jwt_required()
def list_rules():
    user = _get_user(get_jwt_identity())
    q = CommissionRule.query
    if user.company_id:
        q = q.filter_by(company_id=user.company_id)
    else:
        q = q.filter_by(admin_id=user.id)

    rules = q.all()

    # Buscar usuários da empresa para cruzar nomes
    if user.company_id:
        users = {u.id: u for u in User.query.filter_by(company_id=user.company_id).all()}
    else:
        users = {user.id: user}

    return jsonify([{
        "id":          r.id,
        "seller_id":   r.seller_id,
        "seller_name": users.get(r.seller_id, user).name or users.get(r.seller_id, user).email,
        "type":        r.type,
        "value":       r.value,
        "active":      r.active,
        "created_at":  r.created_at,
    } for r in rules]), 200


@commission_bp.route("/commissions/rules", methods=["POST"])
@jwt_required()
def create_rule():
    user = _get_user(get_jwt_identity())
    if user.role != "admin":
        return jsonify({"error": "Apenas admins podem configurar comissões"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados obrigatórios"}), 400

    seller_id = data.get("seller_id")
    rule_type = data.get("type", "percent_total")  # percent_total | percent_profit | fixed
    value     = float(data.get("value", 0))

    if not seller_id:
        return jsonify({"error": "seller_id obrigatório"}), 400
    if rule_type not in ("percent_total", "percent_profit", "fixed"):
        return jsonify({"error": "type inválido"}), 400
    if value <= 0:
        return jsonify({"error": "value deve ser positivo"}), 400

    # Desativa regra anterior do mesmo vendedor se existir
    existing = CommissionRule.query.filter_by(
        seller_id=seller_id,
        company_id=user.company_id,
        active=True
    ).first()
    if existing:
        existing.active = False

    rule = CommissionRule(
        seller_id=seller_id,
        type=rule_type,
        value=value,
        active=True,
        created_at=str(datetime.now().date()),
        admin_id=user.id,
        company_id=user.company_id,
    )
    db.session.add(rule)
    db.session.commit()
    return jsonify({"msg": "Regra criada", "id": rule.id}), 201


@commission_bp.route("/commissions/rules/<int:rule_id>", methods=["PUT"])
@jwt_required()
def update_rule(rule_id):
    user = _get_user(get_jwt_identity())
    if user.role != "admin":
        return jsonify({"error": "Apenas admins"}), 403

    rule = CommissionRule.query.get_or_404(rule_id)
    data = request.get_json()
    if "type"   in data: rule.type  = data["type"]
    if "value"  in data: rule.value = float(data["value"])
    if "active" in data: rule.active= bool(data["active"])
    db.session.commit()
    return jsonify({"msg": "Atualizado"}), 200


@commission_bp.route("/commissions/rules/<int:rule_id>", methods=["DELETE"])
@jwt_required()
def delete_rule(rule_id):
    user = _get_user(get_jwt_identity())
    if user.role != "admin":
        return jsonify({"error": "Apenas admins"}), 403
    rule = CommissionRule.query.get_or_404(rule_id)
    db.session.delete(rule)
    db.session.commit()
    return jsonify({"msg": "Removido"}), 200


# ─────────────────────────────────────────────────────────────────────────────
# RELATÓRIO DE COMISSÕES
# ─────────────────────────────────────────────────────────────────────────────

def _calc_commission(order, rule):
    """Calcula o valor da comissão de um pedido com base na regra."""
    if not rule or not rule.active:
        return 0.0

    if rule.type == "percent_total":
        return round(order.total * rule.value / 100, 2)

    if rule.type == "percent_profit":
        # Calcula lucro estimado: total - custo dos itens
        try:
            items = json.loads(order.items_json or "[]")
            cost  = sum((i.get("cost", 0) or 0) * i.get("qty", 1) for i in items)
            profit= order.total - cost
            return round(max(0, profit) * rule.value / 100, 2)
        except:
            return 0.0

    if rule.type == "fixed":
        return round(rule.value, 2)

    return 0.0


@commission_bp.route("/commissions/report", methods=["GET"])
@jwt_required()
def commission_report():
    user     = _get_user(get_jwt_identity())
    date_from= request.args.get("date_from")
    date_to  = request.args.get("date_to")
    seller_id= request.args.get("seller_id", type=int)

    # Filtrar orders concluídas
    q = Order.query.filter_by(status="done")
    if user.company_id:
        q = q.filter_by(company_id=user.company_id)
    else:
        q = q.filter_by(user_id=user.id)

    # Filtro de data
    orders = []
    for o in q.all():
        d = o.finished_at or o.created_at or ""
        if date_from and d < date_from: continue
        if date_to   and d > date_to:   continue
        orders.append(o)

    # Carregar usuários e regras
    if user.company_id:
        all_users = {u.id: u for u in User.query.filter_by(company_id=user.company_id).all()}
        all_rules = {r.seller_id: r for r in
            CommissionRule.query.filter_by(company_id=user.company_id, active=True).all()}
    else:
        all_users = {user.id: user}
        all_rules = {r.seller_id: r for r in
            CommissionRule.query.filter_by(admin_id=user.id, active=True).all()}

    # Filtro por vendedor
    if seller_id:
        orders = [o for o in orders if (o.seller_id or o.user_id) == seller_id]

    # Montar detalhamento por venda
    sales_detail = []
    totals_by_seller = {}

    for o in sorted(orders, key=lambda x: x.created_at or "", reverse=True):
        vid  = o.seller_id or o.user_id
        rule = all_rules.get(vid)
        comm = _calc_commission(o, rule)
        sname= all_users.get(vid)
        sname= (sname.name or sname.email) if sname else "Desconhecido"

        try:
            items = json.loads(o.items_json or "[]")
        except:
            items = []

        sales_detail.append({
            "order_id":      o.id,
            "order_number":  o.number,
            "seller_id":     vid,
            "seller_name":   sname,
            "date":          o.finished_at or o.created_at,
            "total":         o.total,
            "discount":      o.discount,
            "items_count":   len(items),
            "items":         [{
                "name":  i.get("name",""),
                "qty":   i.get("qty",1),
                "price": i.get("price",0),
                "cost":  i.get("cost",0),
            } for i in items],
            "commission_type":  rule.type if rule else None,
            "commission_rate":  rule.value if rule else None,
            "commission_value": comm,
        })

        if vid not in totals_by_seller:
            totals_by_seller[vid] = {
                "seller_id":        vid,
                "seller_name":      sname,
                "total_sales":      0,
                "total_revenue":    0.0,
                "total_commission": 0.0,
                "commission_type":  rule.type  if rule else None,
                "commission_rate":  rule.value if rule else None,
                "orders":           [],
            }
        totals_by_seller[vid]["total_sales"]      += 1
        totals_by_seller[vid]["total_revenue"]    += o.total
        totals_by_seller[vid]["total_commission"] += comm
        totals_by_seller[vid]["orders"].append(o.number)

    # Ranking por comissão
    ranking = sorted(totals_by_seller.values(), key=lambda x: x["total_commission"], reverse=True)
    for i, r in enumerate(ranking):
        r["rank"] = i + 1
        r["total_revenue"]    = round(r["total_revenue"],    2)
        r["total_commission"] = round(r["total_commission"], 2)

    return jsonify({
        "total_orders":     len(sales_detail),
        "total_revenue":    round(sum(s["total"] for s in sales_detail), 2),
        "total_commission": round(sum(s["commission_value"] for s in sales_detail), 2),
        "by_seller":        ranking,
        "sales":            sales_detail,
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# REATRIBUIR VENDEDOR EM UM ORDER (admin only)
# ─────────────────────────────────────────────────────────────────────────────

@commission_bp.route("/orders/<int:order_id>/seller", methods=["PUT"])
@jwt_required()
def reassign_seller(order_id):
    user = _get_user(get_jwt_identity())
    if user.role != "admin":
        return jsonify({"error": "Apenas admins podem reatribuir vendedor"}), 403

    order = Order.query.get_or_404(order_id)
    data  = request.get_json()
    new_seller_id = data.get("seller_id")
    if not new_seller_id:
        return jsonify({"error": "seller_id obrigatório"}), 400

    # Verifica que o novo vendedor pertence à mesma empresa
    new_seller = User.query.get(new_seller_id)
    if not new_seller:
        return jsonify({"error": "Vendedor não encontrado"}), 404
    if user.company_id and new_seller.company_id != user.company_id:
        return jsonify({"error": "Vendedor não pertence à mesma empresa"}), 403

    order.seller_id = new_seller_id
    db.session.commit()
    return jsonify({"msg": f"Vendedor atualizado para {new_seller.name or new_seller.email}"}), 200