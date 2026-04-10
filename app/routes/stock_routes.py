from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Product, StockMovement, ServiceRecord, User
from datetime import date

stock_bp = Blueprint("stock", __name__)


def _get_user(user_id):
    return User.query.get(int(user_id))


def _find_product(product_id, user):
    if user.company_id:
        return Product.query.filter_by(id=product_id, company_id=user.company_id).first()
    return Product.query.filter_by(id=product_id, user_id=user.id).first()


def _find_service_record(record_id, user):
    if user.company_id:
        return ServiceRecord.query.filter_by(id=record_id, company_id=user.company_id).first()
    return ServiceRecord.query.filter_by(id=record_id, user_id=user.id).first()


@stock_bp.route("/stock/<int:product_id>/movements", methods=["GET"])
@jwt_required()
def get_movements(product_id):
    user    = _get_user(get_jwt_identity())
    product = _find_product(product_id, user)
    if not product:
        return jsonify({"msg": "Produto não encontrado"}), 404

    movements = StockMovement.query.filter_by(product_id=product_id).order_by(StockMovement.id.desc()).all()
    return jsonify([{
        "id":       m.id,
        "type":     m.type,
        "qty":      m.qty,
        "cost":     m.cost,
        "reason":   m.reason,
        "date":     m.date,
        "order_id": m.order_id,
    } for m in movements]), 200


@stock_bp.route("/stock/<int:product_id>/movements", methods=["POST"])
@jwt_required()
def add_movement(product_id):
    user    = _get_user(get_jwt_identity())
    product = _find_product(product_id, user)
    if not product:
        return jsonify({"msg": "Produto não encontrado"}), 404
    if product.type != "product":
        return jsonify({"msg": "Movimentação só se aplica a produtos"}), 400

    data     = request.get_json()
    mov_type = data.get("type")
    qty      = float(data.get("qty", 0))
    cost     = data.get("cost")

    if mov_type not in ["in", "out", "adjust"]:
        return jsonify({"msg": "Tipo inválido. Use: in, out, adjust"}), 400
    if qty <= 0:
        return jsonify({"msg": "Quantidade deve ser maior que zero"}), 400

    if mov_type == "in":
        if cost is not None:
            cost        = float(cost)
            total_value = product.stock_qty * product.stock_avg_cost + qty * cost
            new_qty     = product.stock_qty + qty
            product.stock_avg_cost = total_value / new_qty if new_qty > 0 else cost
        product.stock_qty += qty
    elif mov_type == "out":
        if product.stock_qty < qty:
            return jsonify({"msg": f"Estoque insuficiente. Atual: {product.stock_qty}"}), 400
        product.stock_qty -= qty
    elif mov_type == "adjust":
        product.stock_qty = qty

    movement = StockMovement(
        type       = mov_type,
        qty        = qty,
        cost       = float(cost) if cost is not None else None,
        reason     = data.get("reason", "").strip() or None,
        date       = data.get("date") or str(date.today()),
        product_id = product_id,
        order_id   = data.get("order_id"),
        user_id    = user.id,
        company_id = user.company_id,
    )
    db.session.add(movement)
    db.session.commit()

    return jsonify({
        "msg":            "Movimentação registrada",
        "stock_qty":      product.stock_qty,
        "stock_avg_cost": product.stock_avg_cost,
    }), 201


@stock_bp.route("/stock/alerts", methods=["GET"])
@jwt_required()
def stock_alerts():
    user = _get_user(get_jwt_identity())
    if user.company_id:
        products = Product.query.filter_by(company_id=user.company_id, type="product", active=True).all()
    else:
        products = Product.query.filter_by(user_id=user.id, type="product", active=True).all()

    alerts = [p for p in products if p.stock_qty <= p.stock_min]
    return jsonify([{
        "id":        p.id,
        "name":      p.name,
        "stock_qty": p.stock_qty,
        "stock_min": p.stock_min,
        "unit":      p.unit,
    } for p in alerts]), 200


@stock_bp.route("/services/<int:product_id>/records", methods=["GET"])
@jwt_required()
def get_service_records(product_id):
    user    = _get_user(get_jwt_identity())
    product = _find_product(product_id, user)
    if not product:
        return jsonify({"msg": "Serviço não encontrado"}), 404

    records = ServiceRecord.query.filter_by(product_id=product_id).order_by(ServiceRecord.id.desc()).all()
    return jsonify([{
        "id":           r.id,
        "date":         r.date,
        "duration_min": r.duration_min,
        "amount":       r.amount,
        "notes":        r.notes,
        "client_id":    r.client_id,
        "client_name":  r.client.name if r.client else None,
        "order_id":     r.order_id,
    } for r in records]), 200


@stock_bp.route("/services/<int:product_id>/records", methods=["POST"])
@jwt_required()
def add_service_record(product_id):
    user    = _get_user(get_jwt_identity())
    product = _find_product(product_id, user)
    if not product:
        return jsonify({"msg": "Serviço não encontrado"}), 404
    if product.type != "service":
        return jsonify({"msg": "Registro só se aplica a serviços"}), 400

    data   = request.get_json()
    record = ServiceRecord(
        date         = data.get("date") or str(date.today()),
        duration_min = data.get("duration_min"),
        amount       = float(data.get("amount", product.price)),
        notes        = data.get("notes", "").strip() or None,
        product_id   = product_id,
        client_id    = data.get("client_id"),
        order_id     = data.get("order_id"),
        user_id      = user.id,
        company_id   = user.company_id,
    )
    product.services_count += 1
    db.session.add(record)
    db.session.commit()
    return jsonify({
        "msg":            "Registro de serviço salvo",
        "services_count": product.services_count,
    }), 201


@stock_bp.route("/services/records/<int:record_id>", methods=["DELETE"])
@jwt_required()
def delete_service_record(record_id):
    user   = _get_user(get_jwt_identity())
    record = _find_service_record(record_id, user)
    if not record:
        return jsonify({"msg": "Registro não encontrado"}), 404

    product = record.product
    if product and product.services_count > 0:
        product.services_count -= 1

    db.session.delete(record)
    db.session.commit()
    return jsonify({"msg": "Registro removido"}), 200