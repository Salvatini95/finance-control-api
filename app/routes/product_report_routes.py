from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Product, StockMovement, User, Company
from datetime import datetime

product_report_bp = Blueprint('product_report', __name__)


def _get_user(user_id):
    return User.query.get(int(user_id))


def _fmt_brl(value):
    try:
        v = float(value or 0)
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


@product_report_bp.route('/products/report', methods=['GET'])
@jwt_required()
def get_product_report():
    user = _get_user(get_jwt_identity())

    # ── Filtros ──
    tipo       = request.args.get('tipo', 'all')       # all | product | service
    categoria  = request.args.get('categoria', '')
    status     = request.args.get('status', 'all')     # all | active | inactive
    estoque    = request.args.get('estoque', 'all')    # all | alert | ok | zero
    data_inicio = request.args.get('data_inicio', '')  # para movimentações
    data_fim    = request.args.get('data_fim', '')

    # ── Query produtos ──
    query = Product.query.filter_by(company_id=user.company_id)

    if tipo != 'all':
        query = query.filter_by(type=tipo)
    if categoria:
        query = query.filter(Product.category.ilike(f'%{categoria}%'))
    if status == 'active':
        query = query.filter_by(active=True)
    elif status == 'inactive':
        query = query.filter_by(active=False)

    products = query.order_by(Product.name).all()

    # Filtro de estoque (pós-query)
    if estoque == 'alert':
        products = [p for p in products if p.type == 'product' and p.stock_qty <= p.stock_min and p.stock_qty > 0]
    elif estoque == 'zero':
        products = [p for p in products if p.type == 'product' and p.stock_qty == 0]
    elif estoque == 'ok':
        products = [p for p in products if p.type == 'product' and p.stock_qty > p.stock_min]

    # ── Serializa produtos ──
    produtos_data = []
    for p in products:
        produtos_data.append({
            'id':             p.id,
            'name':           p.name,
            'sku':            p.sku or '—',
            'type':           p.type,
            'category':       p.category or 'Sem categoria',
            'unit':           p.unit or 'un',
            'cost':           p.cost or 0,
            'price':          p.price or 0,
            'profit':         round((p.price or 0) - (p.cost or 0), 2),
            'margin':         p.margin,
            'active':         p.active,
            'stock_qty':      p.stock_qty or 0,
            'stock_min':      p.stock_min or 0,
            'stock_avg_cost': p.stock_avg_cost or 0,
            'services_count': p.services_count or 0,
            'stock_alert':    p.type == 'product' and p.stock_qty <= p.stock_min,
            'stock_value':    round((p.stock_qty or 0) * (p.stock_avg_cost or p.cost or 0), 2),
        })

    # ── Query movimentações ──
    mov_query = StockMovement.query.filter_by(company_id=user.company_id)
    if data_inicio:
        mov_query = mov_query.filter(StockMovement.date >= data_inicio)
    if data_fim:
        mov_query = mov_query.filter(StockMovement.date <= data_fim)

    # Filtra por produto se tipo=product
    if tipo == 'product':
        product_ids = [p.id for p in products]
        if product_ids:
            mov_query = mov_query.filter(StockMovement.product_id.in_(product_ids))

    movimentacoes = mov_query.order_by(StockMovement.date.desc()).all()

    mov_data = []
    for m in movimentacoes:
        product_name = m.product.name if m.product else '—'
        product_sku  = (m.product.sku or '—') if m.product else '—'
        mov_data.append({
            'id':           m.id,
            'product_name': product_name,
            'product_sku':  product_sku,
            'type':         m.type,
            'qty':          m.qty,
            'cost':         m.cost or 0,
            'reason':       m.reason or '—',
            'date':         m.date or '—',
        })

    # ── Indicadores ──
    total_produtos  = len([p for p in produtos_data if p['type'] == 'product'])
    total_servicos  = len([p for p in produtos_data if p['type'] == 'service'])
    total_alertas   = len([p for p in produtos_data if p['stock_alert']])
    valor_estoque   = round(sum(p['stock_value'] for p in produtos_data if p['type'] == 'product'), 2)
    margem_media    = round(sum(p['margin'] for p in produtos_data) / len(produtos_data), 1) if produtos_data else 0
    total_mov_in    = sum(m['qty'] for m in mov_data if m['type'] == 'in')
    total_mov_out   = sum(m['qty'] for m in mov_data if m['type'] == 'out')
    total_mov_ajuste = sum(1 for m in mov_data if m['type'] == 'adjust')

    # Categorias únicas
    categorias = sorted(set(p['category'] for p in produtos_data if p['category'] != 'Sem categoria'))

    # Dados da empresa
    company_name = user.company_name or 'Minha Empresa'
    company_logo = None
    if user.company_id:
        company = Company.query.get(user.company_id)
        if company:
            company_name = company.name
            company_logo = company.logo

    return jsonify({
        'emitido_em':   datetime.now().strftime('%d/%m/%Y às %H:%M'),
        'company_name': company_name,
        'company_logo': company_logo,
        'filtros': {
            'tipo':        tipo,
            'categoria':   categoria,
            'status':      status,
            'estoque':     estoque,
            'data_inicio': data_inicio,
            'data_fim':    data_fim,
        },
        'indicadores': {
            'total_produtos':    total_produtos,
            'total_servicos':    total_servicos,
            'total_alertas':     total_alertas,
            'valor_estoque':     valor_estoque,
            'margem_media':      margem_media,
            'total_mov_in':      total_mov_in,
            'total_mov_out':     total_mov_out,
            'total_mov_ajuste':  total_mov_ajuste,
            'total_mov':         len(mov_data),
        },
        'categorias':     categorias,
        'produtos':       produtos_data,
        'movimentacoes':  mov_data,
    }), 200
