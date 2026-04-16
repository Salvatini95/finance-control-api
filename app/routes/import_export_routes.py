import csv
import io
from datetime import datetime
from flask import Blueprint, request, Response, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import (
    db, User, Transaction, Bill, Client, Product,
    Quote, Order, StockMovement
)

import_export_bp = Blueprint('import_export', __name__)


def get_current_user():
    user_id = get_jwt_identity()
    return User.query.get(user_id)


def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return None


def make_csv_response(rows, headers, filename):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    # BOM para Excel reconhecer UTF-8 com acentos
    bom = '\ufeff'
    return Response(
        bom + output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
    )


# ─────────────────────────────────────────────
# EXPORTAÇÕES
# ─────────────────────────────────────────────

@import_export_bp.route('/export/transactions', methods=['GET'])
@jwt_required()
def export_transactions():
    user = get_current_user()
    date_from = parse_date(request.args.get('date_from'))
    date_to   = parse_date(request.args.get('date_to'))

    q = Transaction.query.filter_by(company_id=user.company_id)
    if date_from:
        q = q.filter(Transaction.date >= date_from)
    if date_to:
        q = q.filter(Transaction.date <= date_to)

    rows = []
    for t in q.order_by(Transaction.date.desc()).all():
        rows.append({
            'ID': t.id,
            'Tipo': t.type,
            'Descrição': t.description,
            'Valor': f'{t.amount:.2f}',
            'Categoria': t.category or '',
            'Data': t.date.strftime('%d/%m/%Y') if t.date else '',
            'Status': t.status or '',
            'Origem': t.source or 'manual',
            'Observações': t.notes or '',
        })

    headers = ['ID', 'Tipo', 'Descrição', 'Valor', 'Categoria', 'Data', 'Status', 'Origem', 'Observações']
    filename = f'transacoes_{datetime.now().strftime("%Y%m%d")}.csv'
    return make_csv_response(rows, headers, filename)


@import_export_bp.route('/export/bills', methods=['GET'])
@jwt_required()
def export_bills():
    user = get_current_user()
    date_from = parse_date(request.args.get('date_from'))
    date_to   = parse_date(request.args.get('date_to'))

    q = Bill.query.filter_by(company_id=user.company_id)
    if date_from:
        q = q.filter(Bill.due_date >= date_from)
    if date_to:
        q = q.filter(Bill.due_date <= date_to)

    rows = []
    for b in q.order_by(Bill.due_date.desc()).all():
        rows.append({
            'ID': b.id,
            'Tipo': b.type,
            'Descrição': b.description,
            'Valor': f'{b.amount:.2f}',
            'Categoria': b.category or '',
            'Vencimento': b.due_date.strftime('%d/%m/%Y') if b.due_date else '',
            'Status': b.status or '',
            'Recorrente': 'Sim' if b.is_recurring else 'Não',
            'Observações': b.notes or '',
        })

    headers = ['ID', 'Tipo', 'Descrição', 'Valor', 'Categoria', 'Vencimento', 'Status', 'Recorrente', 'Observações']
    filename = f'contas_{datetime.now().strftime("%Y%m%d")}.csv'
    return make_csv_response(rows, headers, filename)


@import_export_bp.route('/export/clients', methods=['GET'])
@jwt_required()
def export_clients():
    user = get_current_user()
    date_from = parse_date(request.args.get('date_from'))
    date_to   = parse_date(request.args.get('date_to'))

    q = Client.query.filter_by(company_id=user.company_id)
    if date_from:
        q = q.filter(Client.created_at >= date_from)
    if date_to:
        q = q.filter(Client.created_at <= date_to)

    rows = []
    for c in q.order_by(Client.name).all():
        rows.append({
            'ID': c.id,
            'Nome': c.name,
            'Email': c.email or '',
            'Telefone': c.phone or '',
            'Documento': c.document or '',
            'Endereço': c.address or '',
            'Cidade': c.city or '',
            'Estado': c.state or '',
            'Criado em': c.created_at.strftime('%d/%m/%Y') if c.created_at else '',
            'Observações': c.notes or '',
        })

    headers = ['ID', 'Nome', 'Email', 'Telefone', 'Documento', 'Endereço', 'Cidade', 'Estado', 'Criado em', 'Observações']
    filename = f'clientes_{datetime.now().strftime("%Y%m%d")}.csv'
    return make_csv_response(rows, headers, filename)


@import_export_bp.route('/export/products', methods=['GET'])
@jwt_required()
def export_products():
    user = get_current_user()

    q = Product.query.filter_by(company_id=user.company_id)

    rows = []
    for p in q.order_by(Product.name).all():
        rows.append({
            'ID': p.id,
            'Nome': p.name,
            'SKU': p.sku or '',
            'Tipo': p.type or '',
            'Categoria': p.category or '',
            'Preço de Venda': f'{p.price:.2f}' if p.price else '0.00',
            'Custo': f'{p.cost:.2f}' if p.cost else '0.00',
            'Estoque': p.stock_qty or 0,
            'Estoque Mínimo': p.stock_min or 0,
            'Unidade': p.unit or '',
            'Descrição': p.description or '',
            'Ativo': 'Sim' if p.active else 'Não',
        })

    headers = ['ID', 'Nome', 'SKU', 'Tipo', 'Categoria', 'Preço de Venda', 'Custo',
               'Estoque', 'Estoque Mínimo', 'Unidade', 'Descrição', 'Ativo']
    filename = f'produtos_{datetime.now().strftime("%Y%m%d")}.csv'
    return make_csv_response(rows, headers, filename)


@import_export_bp.route('/export/quotes', methods=['GET'])
@jwt_required()
def export_quotes():
    user = get_current_user()
    date_from = parse_date(request.args.get('date_from'))
    date_to   = parse_date(request.args.get('date_to'))

    q = Quote.query.filter_by(company_id=user.company_id)
    if date_from:
        q = q.filter(Quote.created_at >= date_from)
    if date_to:
        q = q.filter(Quote.created_at <= date_to)

    rows = []
    for qt in q.order_by(Quote.created_at.desc()).all():
        client_name = qt.client.name if qt.client else (qt.client_name or '')
        rows.append({
            'Número': qt.number or qt.id,
            'Cliente': client_name,
            'Status': qt.status or '',
            'Subtotal': f'{qt.subtotal:.2f}' if qt.subtotal else '0.00',
            'Desconto %': f'{qt.discount:.2f}' if qt.discount else '0.00',
            'Total': f'{qt.total:.2f}' if qt.total else '0.00',
            'Validade': qt.valid_until.strftime('%d/%m/%Y') if qt.valid_until else '',
            'Criado em': qt.created_at.strftime('%d/%m/%Y') if qt.created_at else '',
            'Observações': qt.notes or '',
        })

    headers = ['Número', 'Cliente', 'Status', 'Subtotal', 'Desconto %', 'Total', 'Validade', 'Criado em', 'Observações']
    filename = f'orcamentos_{datetime.now().strftime("%Y%m%d")}.csv'
    return make_csv_response(rows, headers, filename)


@import_export_bp.route('/export/sales', methods=['GET'])
@jwt_required()
def export_sales():
    user = get_current_user()
    date_from = parse_date(request.args.get('date_from'))
    date_to   = parse_date(request.args.get('date_to'))

    q = Order.query.filter_by(company_id=user.company_id)
    if date_from:
        q = q.filter(Order.created_at >= date_from)
    if date_to:
        q = q.filter(Order.created_at <= date_to)

    rows = []
    for o in q.order_by(Order.created_at.desc()).all():
        client_name = o.client.name if o.client else ''
        seller_name = o.seller.name if o.seller else ''
        rows.append({
            'Número': o.order_number or o.id,
            'Tipo': o.order_type or '',
            'Cliente': client_name,
            'Vendedor': seller_name,
            'Status': o.status or '',
            'Total': f'{o.total:.2f}' if o.total else '0.00',
            'Origem': 'Orçamento' if o.quote_id else 'Direto',
            'Criado em': o.created_at.strftime('%d/%m/%Y') if o.created_at else '',
            'Concluído em': o.completed_at.strftime('%d/%m/%Y') if o.completed_at else '',
            'Observações': o.notes or '',
        })

    headers = ['Número', 'Tipo', 'Cliente', 'Vendedor', 'Status', 'Total', 'Origem', 'Criado em', 'Concluído em', 'Observações']
    filename = f'vendas_{datetime.now().strftime("%Y%m%d")}.csv'
    return make_csv_response(rows, headers, filename)


# ─────────────────────────────────────────────
# TEMPLATES PARA IMPORTAÇÃO (download)
# ─────────────────────────────────────────────

TEMPLATES = {
    'transactions': {
        'filename': 'template_transacoes.csv',
        'headers': ['Tipo', 'Descrição', 'Valor', 'Categoria', 'Data', 'Status', 'Observações'],
        'example': {
            'Tipo': 'receita',
            'Descrição': 'Venda de produto',
            'Valor': '150.00',
            'Categoria': 'Vendas',
            'Data': '01/01/2025',
            'Status': 'confirmado',
            'Observações': ''
        }
    },
    'bills': {
        'filename': 'template_contas.csv',
        'headers': ['Tipo', 'Descrição', 'Valor', 'Categoria', 'Vencimento', 'Status', 'Observações'],
        'example': {
            'Tipo': 'pagar',
            'Descrição': 'Aluguel',
            'Valor': '1200.00',
            'Categoria': 'Aluguel',
            'Vencimento': '10/01/2025',
            'Status': 'pendente',
            'Observações': ''
        }
    },
    'clients': {
        'filename': 'template_clientes.csv',
        'headers': ['Nome', 'Email', 'Telefone', 'Documento', 'Endereço', 'Cidade', 'Estado', 'Observações'],
        'example': {
            'Nome': 'João da Silva',
            'Email': 'joao@email.com',
            'Telefone': '(44) 99999-0000',
            'Documento': '123.456.789-00',
            'Endereço': 'Rua das Flores, 100',
            'Cidade': 'Maringá',
            'Estado': 'PR',
            'Observações': ''
        }
    },
    'products': {
        'filename': 'template_produtos.csv',
        'headers': ['Nome', 'SKU', 'Tipo', 'Categoria', 'Preço de Venda', 'Custo', 'Estoque', 'Estoque Mínimo', 'Unidade', 'Descrição'],
        'example': {
            'Nome': 'Produto Exemplo',
            'SKU': 'PROD-001',
            'Tipo': 'produto',
            'Categoria': 'Geral',
            'Preço de Venda': '50.00',
            'Custo': '25.00',
            'Estoque': '10',
            'Estoque Mínimo': '2',
            'Unidade': 'un',
            'Descrição': ''
        }
    }
}


@import_export_bp.route('/export/template/<module>', methods=['GET'])
@jwt_required()
def download_template(module):
    if module not in TEMPLATES:
        return jsonify({'error': 'Módulo inválido'}), 400

    tpl = TEMPLATES[module]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=tpl['headers'])
    writer.writeheader()
    writer.writerow(tpl['example'])
    output.seek(0)
    bom = '\ufeff'

    return Response(
        bom + output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="{tpl["filename"]}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
    )


# ─────────────────────────────────────────────
# IMPORTAÇÃO — apenas retorna preview (Fase 2)
# ─────────────────────────────────────────────

@import_export_bp.route('/import/preview', methods=['POST'])
@jwt_required()
def import_preview():
    """
    Recebe um CSV, detecta o sistema de origem e retorna:
    - colunas detectadas
    - sistema detectado (generico/conta_azul/nibo/etc)
    - sugestão de mapeamento
    - primeiras 5 linhas para preview
    Fase 2 implementará o mapeamento interativo no frontend.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    file = request.files['file']
    content = file.read().decode('utf-8-sig')  # utf-8-sig remove BOM
    reader = csv.DictReader(io.StringIO(content))
    columns = reader.fieldnames or []
    rows = []
    for i, row in enumerate(reader):
        if i >= 5:
            break
        rows.append(dict(row))

    # Detecção simples de sistema de origem
    col_set = set(c.lower() for c in columns)
    detected_system = 'generico'

    if 'competência' in col_set or 'plano de contas' in col_set:
        detected_system = 'conta_azul'
    elif 'histórico' in col_set and 'débito' in col_set and 'crédito' in col_set:
        detected_system = 'nibo'
    elif 'serviço' in col_set and 'profissional' in col_set:
        detected_system = 'app_barber'

    return jsonify({
        'columns': columns,
        'detected_system': detected_system,
        'preview_rows': rows,
        'total_columns': len(columns)
    })
