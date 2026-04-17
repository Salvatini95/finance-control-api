import csv
import io
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User, Transaction, Bill, Client, Product, StockMovement, Order
from functools import wraps

import_bp = Blueprint('import', __name__)


def get_current_user():
    return User.query.get(get_jwt_identity())


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user or user.role != 'admin':
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def safe_float(val, default=0.0):
    try:
        return float(str(val).replace(',', '.').strip())
    except Exception:
        return default


def safe_date_str(val):
    """Converte qualquer formato de data para string yyyy-mm-dd."""
    if not val:
        return None
    val = str(val).strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(val, fmt).strftime('%Y-%m-%d')
        except Exception:
            continue
    return None


def parse_csv_or_xlsx(file):
    """Lê arquivo CSV ou XLSX e retorna (headers, rows)."""
    fname = file.filename or ''
    if fname.endswith('.xlsx') or fname.endswith('.xls'):
        try:
            import openpyxl
            wb   = openpyxl.load_workbook(io.BytesIO(file.read()), data_only=True)
            ws   = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return [], []
            headers = [str(c).strip() if c is not None else '' for c in rows[0]]
            data    = []
            for row in rows[1:]:
                data.append({headers[i]: (str(row[i]).strip() if row[i] is not None else '') for i in range(len(headers))})
            return headers, data
        except ImportError:
            return [], []
    else:
        content = file.read().decode('utf-8-sig')
        reader  = csv.DictReader(io.StringIO(content))
        headers = list(reader.fieldnames or [])
        data    = [dict(row) for row in reader]
        return headers, data


def resolve(row, field, mapping, aliases):
    """Resolve valor de um campo via mapping explícito ou alias automático."""
    if field in mapping and mapping[field] in row:
        return str(row[mapping[field]]).strip()
    for alias in aliases:
        if alias in row:
            return str(row[alias]).strip()
    return ''


def _next_order_number(user, prefix='PED'):
    """Gera número sequencial por prefixo e ano."""
    year = datetime.today().year
    if user.company_id:
        all_orders = Order.query.filter_by(company_id=user.company_id).all()
    else:
        all_orders = Order.query.filter_by(user_id=user.id).all()
    count = sum(1 for o in all_orders if o.number.startswith(f'{prefix}-{year}')) + 1
    return f'{prefix}-{year}-{count:03d}'


def _find_or_create_client(client_name, user):
    """Encontra cliente pelo nome ou cria um novo."""
    if not client_name or client_name.strip() == '':
        return None
    existing = Client.query.filter_by(
        company_id=user.company_id,
        name=client_name.strip()
    ).first()
    if existing:
        return existing
    new_client = Client(
        name       = client_name.strip(),
        company_id = user.company_id,
        user_id    = user.id,
        created_at = datetime.today().strftime('%Y-%m-%d'),
    )
    db.session.add(new_client)
    db.session.flush()
    return new_client


def _is_sale_source(raw_source, raw_type):
    """Detecta se a linha representa uma venda."""
    source_lower = raw_source.lower()
    return source_lower in (
        'sale', 'venda', 'vendas', 'pedido', 'ped', 'os',
        'ordem de servico', 'ordem de serviço', 'order'
    ) or (
        raw_type in ('income', 'receita') and
        source_lower in ('sale', 'venda', 'vendas')
    )


# ─────────────────────────────────────────────
# ROTA PRINCIPAL
# ─────────────────────────────────────────────

@import_bp.route('/import/<module>', methods=['POST'])
@jwt_required()
def import_module(module):
    user = get_current_user()

    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    mapping_raw = request.form.get('mapping', '{}')
    try:
        mapping = json.loads(mapping_raw)
    except Exception:
        mapping = {}

    file          = request.files['file']
    headers, rows = parse_csv_or_xlsx(file)

    if not rows:
        return jsonify({'error': 'Arquivo vazio ou inválido'}), 400

    handlers = {
        'transactions': import_transactions,
        'bills':        import_bills,
        'clients':      import_clients,
        'products':     import_products,
        'team':         import_team,
    }

    if module not in handlers:
        return jsonify({'error': f'Módulo "{module}" não suporta importação'}), 400

    result = handlers[module](rows, mapping, user)
    db.session.commit()
    return jsonify(result)


# ─────────────────────────────────────────────
# TRANSAÇÕES
# Detecta automaticamente se é venda e cria Order
# ─────────────────────────────────────────────

def import_transactions(rows, mapping, user):
    imported          = 0
    skipped           = 0
    orders_created    = 0
    errors            = []
    orders_no_client  = []  # ordens criadas sem cliente identificado

    ALIASES = {
        'type':        ['Tipo', 'tipo', 'Natureza', 'natureza'],
        'description': ['Descrição', 'descricao', 'Histórico', 'historico', 'Description', 'Memo'],
        'amount':      ['Valor', 'valor', 'Amount', 'Valor Lançamento'],
        'category':    ['Categoria', 'categoria', 'Category', 'Plano de Contas'],
        'date':        ['Data', 'data', 'Date', 'Competência', 'competencia', 'Data Lançamento'],
        'source':      ['Origem', 'origem', 'Source', 'Fonte', 'Tipo Lançamento'],
        # campos opcionais para compor a order
        'client':      ['Cliente', 'cliente', 'Client', 'Razão Social', 'Sacado'],
        'item_name':   ['Produto', 'produto', 'Item', 'item', 'Serviço', 'servico', 'Descrição do Item'],
        'item_qty':    ['Quantidade', 'quantidade', 'Qtd', 'qtd', 'Qty'],
        'item_price':  ['Preço Unitário', 'preco_unitario', 'Unit Price', 'Preço Unit', 'Vlr Unit'],
        'order_number':['Número Pedido', 'numero_pedido', 'N. Pedido', 'Order Number', 'Nº OS', 'Nº Pedido'],
    }

    today = datetime.today().strftime('%Y-%m-%d')

    for i, row in enumerate(rows, start=2):
        try:
            # ── Tipo ──────────────────────────────────────
            raw_type = resolve(row, 'type', mapping, ALIASES['type']).lower()
            if raw_type in ('receita', 'entrada', 'recebimento', 'income', 'c', 'crédito', 'credito'):
                t_type = 'income'
            elif raw_type in ('despesa', 'saída', 'saida', 'pagamento', 'expense', 'd', 'débito', 'debito'):
                t_type = 'expense'
            else:
                errors.append({'row': i, 'field': 'Tipo', 'message': f'Valor "{raw_type}" não reconhecido. Use: receita ou despesa'})
                skipped += 1
                continue

            # ── Descrição (obrigatório) ───────────────────
            description = resolve(row, 'description', mapping, ALIASES['description'])
            if not description:
                errors.append({'row': i, 'field': 'Descrição', 'message': 'Descrição obrigatória'})
                skipped += 1
                continue

            # ── Valor (obrigatório) ───────────────────────
            raw_amount = resolve(row, 'amount', mapping, ALIASES['amount'])
            amount     = safe_float(raw_amount)
            if amount <= 0:
                errors.append({'row': i, 'field': 'Valor', 'message': f'Valor "{raw_amount}" inválido ou zero'})
                skipped += 1
                continue

            category = resolve(row, 'category', mapping, ALIASES['category']) or 'Importado'
            date_str = safe_date_str(resolve(row, 'date', mapping, ALIASES['date'])) or today

            # ── Detecta se é venda ────────────────────────
            raw_source     = resolve(row, 'source', mapping, ALIASES['source'])
            is_sale        = t_type == 'income' and _is_sale_source(raw_source, t_type)
            source_final   = 'sale' if is_sale else ('import' if not raw_source else raw_source.lower()[:20])

            # ── Cria a Transação ──────────────────────────
            t = Transaction(
                company_id  = user.company_id,
                user_id     = user.id,
                type        = t_type,
                description = description,
                amount      = amount,
                category    = category,
                date        = date_str,
                source      = source_final,
            )
            db.session.add(t)
            db.session.flush()  # gera t.id antes de criar a Order
            imported += 1

            # ── Se for venda → cria Order vinculada ───────
            if is_sale:
                client_name    = resolve(row, 'client',       mapping, ALIASES['client'])
                item_name      = resolve(row, 'item_name',    mapping, ALIASES['item_name'])  or description
                item_qty       = safe_float(resolve(row, 'item_qty',   mapping, ALIASES['item_qty']),  1.0)
                item_price     = safe_float(resolve(row, 'item_price', mapping, ALIASES['item_price']), amount)
                order_number_csv = resolve(row, 'order_number', mapping, ALIASES['order_number'])

                # Encontra ou cria cliente
                client_obj = _find_or_create_client(client_name, user)
                client_id  = client_obj.id if client_obj else None

                # Monta item único da order
                item_total = item_qty * item_price
                items_list = [{
                    'name':       item_name,
                    'unit':       'un',
                    'qty':        item_qty,
                    'price':      item_price,
                    'total':      item_total,
                    'product_id': None,
                }]

                # Define prefixo (OS se vier "OS" na descrição ou Origem, PED caso contrário)
                desc_lower = description.lower()
                src_lower  = raw_source.lower()
                if 'os-' in desc_lower or 'os ' in desc_lower or src_lower in ('os','ordem de servico','ordem de serviço'):
                    prefix = 'OS'
                else:
                    prefix = 'PED'

                # Usa número do CSV se existir, senão gera
                order_num = order_number_csv if order_number_csv else _next_order_number(user, prefix)

                order = Order(
                    number         = order_num,
                    status         = 'done',
                    origin         = 'import',
                    notes          = f'Importado via CSV — {date_str}',
                    payment_terms  = '',
                    discount       = 0.0,
                    items_json     = json.dumps(items_list),
                    subtotal       = amount,
                    total          = amount,
                    created_at     = date_str,
                    finished_at    = date_str,
                    client_id      = client_id,
                    quote_id       = None,
                    transaction_id = t.id,
                    user_id        = user.id,
                    company_id     = user.company_id,
                )
                db.session.add(order)
                db.session.flush()

                # Vincula transaction → order (para o link clicável funcionar)
                # transaction_id já está na order; order_id vai no lookup do GET /transactions

                orders_created += 1

                # Notifica se não tem cliente
                if not client_id:
                    orders_no_client.append({
                        'row':          i,
                        'order_number': order_num,
                        'description':  description,
                        'message':      'Venda criada sem cliente — preencha manualmente em Vendas',
                    })

        except Exception as e:
            errors.append({'row': i, 'field': '—', 'message': str(e)})
            skipped += 1

    # Monta info final
    info = ''
    if orders_created > 0:
        info = (
            f'{orders_created} venda(s) criada(s) automaticamente. '
            'Clique no número do pedido em Transações para visualizar.'
        )

    return {
        'imported':            imported,
        'skipped':             skipped,
        'updated':             0,
        'errors':              errors,
        'duplicates_notified': [],
        'orders_created':      orders_created,
        'orders_no_client':    orders_no_client,
        'info':                info,
    }


# ─────────────────────────────────────────────
# CONTAS (BILLS)
# ─────────────────────────────────────────────

def import_bills(rows, mapping, user):
    imported = 0
    skipped  = 0
    errors   = []

    ALIASES = {
        'type':        ['Tipo', 'tipo', 'Natureza'],
        'description': ['Descrição', 'descricao', 'Histórico', 'historico'],
        'amount':      ['Valor', 'valor', 'Amount'],
        'due_date':    ['Vencimento', 'vencimento', 'Data Vencimento', 'Due Date'],
        'category':    ['Categoria', 'categoria'],
        'status':      ['Status', 'status', 'Situação'],
        'notes':       ['Observações', 'observacoes', 'Obs'],
    }

    for i, row in enumerate(rows, start=2):
        try:
            raw_type = resolve(row, 'type', mapping, ALIASES['type']).lower()
            if raw_type in ('pagar', 'despesa', 'saída', 'saida', 'payable', 'a pagar'):
                b_type = 'payable'
            elif raw_type in ('receber', 'receita', 'entrada', 'receivable', 'a receber'):
                b_type = 'receivable'
            else:
                errors.append({'row': i, 'field': 'Tipo', 'message': f'Valor "{raw_type}" não reconhecido. Use: pagar ou receber'})
                skipped += 1
                continue

            description = resolve(row, 'description', mapping, ALIASES['description'])
            if not description:
                errors.append({'row': i, 'field': 'Descrição', 'message': 'Descrição obrigatória'})
                skipped += 1
                continue

            raw_amount = resolve(row, 'amount', mapping, ALIASES['amount'])
            amount     = safe_float(raw_amount)
            if amount <= 0:
                errors.append({'row': i, 'field': 'Valor', 'message': f'Valor "{raw_amount}" inválido ou zero'})
                skipped += 1
                continue

            raw_date = resolve(row, 'due_date', mapping, ALIASES['due_date'])
            due_date = safe_date_str(raw_date)
            if not due_date:
                errors.append({'row': i, 'field': 'Vencimento', 'message': f'Data "{raw_date}" inválida. Use dd/mm/aaaa'})
                skipped += 1
                continue

            category = resolve(row, 'category', mapping, ALIASES['category']) or 'Importado'
            status   = resolve(row, 'status',   mapping, ALIASES['status'])   or 'pending'
            notes    = resolve(row, 'notes',    mapping, ALIASES['notes'])    or None

            b = Bill(
                company_id  = user.company_id,
                user_id     = user.id,
                type        = b_type,
                description = description,
                amount      = amount,
                category    = category,
                due_date    = due_date,
                status      = status,
                notes       = notes,
            )
            db.session.add(b)
            imported += 1

        except Exception as e:
            errors.append({'row': i, 'field': '—', 'message': str(e)})
            skipped += 1

    return {'imported': imported, 'skipped': skipped, 'updated': 0, 'errors': errors, 'duplicates_notified': []}


# ─────────────────────────────────────────────
# CLIENTES
# ─────────────────────────────────────────────

def import_clients(rows, mapping, user):
    imported   = 0
    skipped    = 0
    updated    = 0
    errors     = []
    duplicates = []

    ALIASES = {
        'name':     ['Nome', 'nome', 'Name', 'Cliente', 'Razão Social'],
        'email':    ['Email', 'email', 'E-mail'],
        'phone':    ['Telefone', 'telefone', 'Phone', 'Celular'],
        'document': ['Documento', 'documento', 'CPF', 'CNPJ', 'CPF/CNPJ'],
        'address':  ['Endereço', 'endereco', 'Address', 'Logradouro'],
        'notes':    ['Observações', 'observacoes', 'Obs', 'Nota'],
    }

    for i, row in enumerate(rows, start=2):
        try:
            name = resolve(row, 'name', mapping, ALIASES['name'])
            if not name:
                errors.append({'row': i, 'field': 'Nome', 'message': 'Nome obrigatório'})
                skipped += 1
                continue

            email    = resolve(row, 'email',    mapping, ALIASES['email'])    or None
            phone    = resolve(row, 'phone',    mapping, ALIASES['phone'])    or None
            document = resolve(row, 'document', mapping, ALIASES['document']) or None
            address  = resolve(row, 'address',  mapping, ALIASES['address'])  or None
            notes    = resolve(row, 'notes',    mapping, ALIASES['notes'])    or None

            existing = Client.query.filter_by(company_id=user.company_id, name=name).first()

            if existing:
                has_conflict = (
                    (email    and existing.email    and existing.email    != email)    or
                    (document and existing.document and existing.document != document) or
                    (phone    and existing.phone    and existing.phone    != phone)
                )
                if has_conflict:
                    duplicates.append({
                        'name':    name,
                        'message': 'Nome já existe com email/documento/telefone diferente',
                        'row':     i,
                    })
                if email:    existing.email    = email
                if phone:    existing.phone    = phone
                if document: existing.document = document
                if address:  existing.address  = address
                if notes:    existing.notes    = notes
                updated += 1
            else:
                today = datetime.today().strftime('%Y-%m-%d')
                c = Client(
                    company_id = user.company_id,
                    user_id    = user.id,
                    name       = name,
                    email      = email,
                    phone      = phone,
                    document   = document,
                    address    = address,
                    notes      = notes,
                    created_at = today,
                )
                db.session.add(c)
                imported += 1

        except Exception as e:
            errors.append({'row': i, 'field': '—', 'message': str(e)})
            skipped += 1

    return {
        'imported':            imported,
        'skipped':             skipped,
        'updated':             updated,
        'errors':              errors,
        'duplicates_notified': duplicates,
    }


# ─────────────────────────────────────────────
# PRODUTOS
# ─────────────────────────────────────────────

def import_products(rows, mapping, user):
    imported   = 0
    skipped    = 0
    updated    = 0
    errors     = []
    duplicates = []

    ALIASES = {
        'name':        ['Nome', 'nome', 'Produto', 'Name'],
        'sku':         ['SKU', 'sku', 'Código', 'Cod', 'Referência', 'Ref'],
        'type':        ['Tipo', 'tipo', 'Type'],
        'category':    ['Categoria', 'categoria', 'Category'],
        'price':       ['Preço de Venda', 'preco_venda', 'Preço', 'Price', 'Valor Venda'],
        'cost':        ['Custo', 'custo', 'Cost', 'Valor Custo'],
        'stock_qty':   ['Estoque', 'estoque', 'Stock', 'Qtd', 'Quantidade'],
        'stock_min':   ['Estoque Mínimo', 'estoque_min', 'Min Stock', 'Qtd Mínima'],
        'unit':        ['Unidade', 'unidade', 'Unit', 'Un'],
        'description': ['Descrição', 'descricao', 'Description', 'Obs'],
    }

    today = datetime.today().strftime('%Y-%m-%d')

    for i, row in enumerate(rows, start=2):
        try:
            name = resolve(row, 'name', mapping, ALIASES['name'])
            if not name:
                errors.append({'row': i, 'field': 'Nome', 'message': 'Nome obrigatório'})
                skipped += 1
                continue

            sku         = resolve(row, 'sku',         mapping, ALIASES['sku'])         or None
            p_type      = resolve(row, 'type',        mapping, ALIASES['type']).lower() or 'produto'
            category    = resolve(row, 'category',    mapping, ALIASES['category'])    or 'Importado'
            price       = safe_float(resolve(row, 'price',       mapping, ALIASES['price']))
            cost        = safe_float(resolve(row, 'cost',        mapping, ALIASES['cost']))
            stock_qty   = safe_float(resolve(row, 'stock_qty',   mapping, ALIASES['stock_qty']))
            stock_min   = safe_float(resolve(row, 'stock_min',   mapping, ALIASES['stock_min']))
            unit        = resolve(row, 'unit',        mapping, ALIASES['unit'])        or 'un'
            description = resolve(row, 'description', mapping, ALIASES['description']) or None

            if p_type in ('produto', 'product', 'prod'):
                p_type = 'product'
            elif p_type in ('serviço', 'servico', 'service', 'svc'):
                p_type = 'service'
            else:
                p_type = 'product'

            existing = None
            if sku:
                existing = Product.query.filter_by(company_id=user.company_id, sku=sku).first()
            if not existing:
                existing = Product.query.filter_by(company_id=user.company_id, name=name).first()

            if existing:
                has_conflict = (
                    (price > 0 and existing.price and abs(existing.price - price) > 0.01) or
                    (cost  > 0 and existing.cost  and abs(existing.cost  - cost)  > 0.01)
                )
                if has_conflict:
                    duplicates.append({
                        'name':    name,
                        'sku':     sku or '—',
                        'message': 'Produto já existe com preço/custo diferente',
                        'row':     i,
                    })
                if sku:         existing.sku         = sku
                if price > 0:   existing.price       = price
                if cost  > 0:   existing.cost        = cost
                if stock_qty:   existing.stock_qty   = stock_qty
                if stock_min:   existing.stock_min   = stock_min
                if unit:        existing.unit        = unit
                if description: existing.description = description
                if category:    existing.category    = category
                updated += 1

                if stock_qty > 0:
                    mv = StockMovement(
                        company_id = user.company_id,
                        product_id = existing.id,
                        user_id    = user.id,
                        type       = 'ajuste',
                        qty        = stock_qty,
                        reason     = 'Ajuste via importação CSV',
                        date       = today,
                    )
                    db.session.add(mv)
            else:
                p = Product(
                    company_id  = user.company_id,
                    user_id     = user.id,
                    name        = name,
                    sku         = sku,
                    type        = p_type,
                    category    = category,
                    price       = price,
                    cost        = cost,
                    stock_qty   = stock_qty,
                    stock_min   = stock_min,
                    unit        = unit,
                    description = description,
                    active      = True,
                )
                db.session.add(p)
                db.session.flush()

                if stock_qty > 0:
                    mv = StockMovement(
                        company_id = user.company_id,
                        product_id = p.id,
                        user_id    = user.id,
                        type       = 'entrada',
                        qty        = stock_qty,
                        reason     = 'Estoque inicial via importação CSV',
                        date       = today,
                    )
                    db.session.add(mv)

                imported += 1

        except Exception as e:
            errors.append({'row': i, 'field': '—', 'message': str(e)})
            skipped += 1

    return {
        'imported':            imported,
        'skipped':             skipped,
        'updated':             updated,
        'errors':              errors,
        'duplicates_notified': duplicates,
    }


# ─────────────────────────────────────────────
# EQUIPE (somente admin)
# ─────────────────────────────────────────────

def import_team(rows, mapping, user):
    if user.role != 'admin':
        return {'error': 'Apenas admins podem importar membros da equipe'}

    imported   = 0
    skipped    = 0
    updated    = 0
    errors     = []
    duplicates = []

    ROLES_VALID = ['admin', 'financial', 'stock', 'seller', 'viewer']

    ALIASES = {
        'name':  ['Nome', 'nome', 'Name'],
        'email': ['Email', 'email', 'E-mail'],
        'role':  ['Role', 'role', 'Função', 'Perfil', 'Cargo'],
        'active':['Ativo', 'ativo', 'Active', 'Status'],
    }

    for i, row in enumerate(rows, start=2):
        try:
            name = resolve(row, 'name', mapping, ALIASES['name'])
            if not name:
                errors.append({'row': i, 'field': 'Nome', 'message': 'Nome obrigatório'})
                skipped += 1
                continue

            email = resolve(row, 'email', mapping, ALIASES['email'])
            if not email:
                errors.append({'row': i, 'field': 'Email', 'message': 'Email obrigatório'})
                skipped += 1
                continue

            role = resolve(row, 'role', mapping, ALIASES['role']).lower() or 'viewer'
            if role not in ROLES_VALID:
                errors.append({'row': i, 'field': 'Role', 'message': f'Role "{role}" inválido. Use: {", ".join(ROLES_VALID)}'})
                skipped += 1
                continue

            raw_active = resolve(row, 'active', mapping, ALIASES['active']).lower()
            active = raw_active not in ('não', 'nao', 'false', '0', 'inativo')

            from app.models import User as UserModel
            existing = UserModel.query.filter_by(email=email).first()

            if existing:
                if existing.company_id and existing.company_id != user.company_id:
                    duplicates.append({
                        'name':    name,
                        'message': f'Email {email} já pertence a outra empresa',
                        'row':     i,
                    })
                    skipped += 1
                    continue

                existing.name       = name
                existing.role       = role
                existing.active     = active
                existing.company_id = user.company_id
                updated += 1
            else:
                import secrets
                temp_password = secrets.token_hex(16)

                new_user = UserModel(
                    name           = name,
                    email          = email,
                    role           = role,
                    active         = active,
                    account_type   = 'business',
                    company_id     = user.company_id,
                    email_verified = False,
                )
                new_user.set_password(temp_password)
                db.session.add(new_user)
                imported += 1

        except Exception as e:
            errors.append({'row': i, 'field': '—', 'message': str(e)})
            skipped += 1

    info = ''
    if imported > 0:
        info = 'Membros importados precisam usar "Esqueci minha senha" para definir sua senha e acessar o sistema.'

    return {
        'imported':            imported,
        'skipped':             skipped,
        'updated':             updated,
        'errors':              errors,
        'duplicates_notified': duplicates,
        'info':                info,
    }