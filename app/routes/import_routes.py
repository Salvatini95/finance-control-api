import csv
import io
from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, User, Transaction, Bill, Client, Product, StockMovement

import_bp = Blueprint('import', __name__)


def get_current_user():
    return User.query.get(get_jwt_identity())


def safe_float(val, default=0.0):
    try:
        return float(str(val).replace(',', '.').strip())
    except Exception:
        return default


def safe_date(val):
    if not val:
        return None
    val = str(val).strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(val, fmt).date()
        except Exception:
            continue
    return None


def parse_csv_or_xlsx(file):
    """Lê arquivo CSV ou XLSX e retorna lista de dicts."""
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


# ─────────────────────────────────────────────
# ROTA PRINCIPAL DE IMPORTAÇÃO
# ─────────────────────────────────────────────

@import_bp.route('/import/<module>', methods=['POST'])
@jwt_required()
def import_module(module):
    """
    Recebe:
      - file: arquivo CSV ou XLSX
      - mapping: JSON com { campo_sistema: coluna_arquivo } ex: {"description": "Histórico"}

    Retorna:
      - imported: int
      - skipped: int
      - updated: int
      - errors: list de { row, field, message }
      - duplicates_notified: list de registros que foram atualizados
    """
    user = get_current_user()

    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    import json
    mapping_raw = request.form.get('mapping', '{}')
    try:
        mapping = json.loads(mapping_raw)
    except Exception:
        mapping = {}

    file             = request.files['file']
    headers, rows    = parse_csv_or_xlsx(file)

    if not rows:
        return jsonify({'error': 'Arquivo vazio ou inválido'}), 400

    handlers = {
        'transactions': import_transactions,
        'bills':        import_bills,
        'clients':      import_clients,
        'products':     import_products,
    }

    if module not in handlers:
        return jsonify({'error': f'Módulo "{module}" não suporta importação ainda'}), 400

    result = handlers[module](rows, mapping, user)
    db.session.commit()
    return jsonify(result)


def resolve(row, field, mapping, aliases):
    """
    Resolve valor de um campo.
    Prioridade: mapping explícito → alias automático → campo direto.
    """
    # 1. Mapeamento manual explícito
    if field in mapping and mapping[field] in row:
        return str(row[mapping[field]]).strip()
    # 2. Alias automático por nome de coluna
    for alias in aliases:
        if alias in row:
            return str(row[alias]).strip()
    return ''


# ─────────────────────────────────────────────
# IMPORTAR TRANSAÇÕES
# ─────────────────────────────────────────────

def import_transactions(rows, mapping, user):
    imported = 0
    skipped  = 0
    errors   = []

    ALIASES = {
        'type':        ['Tipo', 'tipo', 'Type', 'Natureza', 'natureza'],
        'description': ['Descrição', 'descricao', 'Histórico', 'historico', 'Description', 'Memo'],
        'amount':      ['Valor', 'valor', 'Amount', 'Valor Lançamento', 'Vlr Lançamento'],
        'category':    ['Categoria', 'categoria', 'Category', 'Plano de Contas'],
        'date':        ['Data', 'data', 'Date', 'Competência', 'competencia', 'Data Lançamento'],
        'status':      ['Status', 'status', 'Situação'],
        'notes':       ['Observações', 'observacoes', 'Obs', 'Memo', 'Complemento'],
    }

    for i, row in enumerate(rows, start=2):
        try:
            raw_type = resolve(row, 'type', mapping, ALIASES['type']).lower()
            if raw_type in ('receita', 'entrada', 'recebimento', 'income', 'c', 'crédito', 'credito'):
                t_type = 'income'
            elif raw_type in ('despesa', 'saída', 'saida', 'pagamento', 'expense', 'd', 'débito', 'debito'):
                t_type = 'expense'
            else:
                errors.append({'row': i, 'field': 'Tipo', 'message': f'Valor "{raw_type}" não reconhecido. Use: receita/despesa'})
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

            raw_date = resolve(row, 'date', mapping, ALIASES['date'])
            t_date   = safe_date(raw_date) or date.today()

            category = resolve(row, 'category', mapping, ALIASES['category']) or 'Importado'
            status   = resolve(row, 'status',   mapping, ALIASES['status'])   or 'confirmado'
            notes    = resolve(row, 'notes',    mapping, ALIASES['notes'])

            t = Transaction(
                company_id  = user.company_id,
                type        = t_type,
                description = description,
                amount      = amount,
                category    = category,
                date        = t_date,
                status      = status,
                notes       = notes,
                source      = 'import',
            )
            db.session.add(t)
            imported += 1

        except Exception as e:
            errors.append({'row': i, 'field': '—', 'message': str(e)})
            skipped += 1

    return {'imported': imported, 'skipped': skipped, 'updated': 0, 'errors': errors, 'duplicates_notified': []}


# ─────────────────────────────────────────────
# IMPORTAR CONTAS (BILLS)
# ─────────────────────────────────────────────

def import_bills(rows, mapping, user):
    imported = 0
    skipped  = 0
    errors   = []

    ALIASES = {
        'type':        ['Tipo', 'tipo', 'Natureza'],
        'description': ['Descrição', 'descricao', 'Histórico', 'historico'],
        'amount':      ['Valor', 'valor', 'Amount'],
        'category':    ['Categoria', 'categoria'],
        'due_date':    ['Vencimento', 'vencimento', 'Data Vencimento', 'Due Date'],
        'status':      ['Status', 'status', 'Situação'],
        'notes':       ['Observações', 'observacoes', 'Obs'],
    }

    for i, row in enumerate(rows, start=2):
        try:
            raw_type = resolve(row, 'type', mapping, ALIASES['type']).lower()
            if raw_type in ('pagar', 'despesa', 'saída', 'saida', 'payable'):
                b_type = 'payable'
            elif raw_type in ('receber', 'receita', 'entrada', 'receivable'):
                b_type = 'receivable'
            else:
                errors.append({'row': i, 'field': 'Tipo', 'message': f'Valor "{raw_type}" não reconhecido. Use: pagar/receber'})
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
            due_date = safe_date(raw_date)
            if not due_date:
                errors.append({'row': i, 'field': 'Vencimento', 'message': f'Data "{raw_date}" inválida. Use dd/mm/aaaa'})
                skipped += 1
                continue

            category = resolve(row, 'category', mapping, ALIASES['category']) or 'Importado'
            status   = resolve(row, 'status',   mapping, ALIASES['status'])   or 'pending'
            notes    = resolve(row, 'notes',    mapping, ALIASES['notes'])

            b = Bill(
                company_id  = user.company_id,
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
# IMPORTAR CLIENTES
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
        'phone':    ['Telefone', 'telefone', 'Phone', 'Celular', 'Fone'],
        'document': ['Documento', 'documento', 'CPF', 'CNPJ', 'CPF/CNPJ'],
        'address':  ['Endereço', 'endereco', 'Address', 'Logradouro'],
        'city':     ['Cidade', 'cidade', 'City'],
        'state':    ['Estado', 'estado', 'UF', 'State'],
        'notes':    ['Observações', 'observacoes', 'Obs'],
    }

    for i, row in enumerate(rows, start=2):
        try:
            name = resolve(row, 'name', mapping, ALIASES['name'])
            if not name:
                errors.append({'row': i, 'field': 'Nome', 'message': 'Nome obrigatório'})
                skipped += 1
                continue

            email    = resolve(row, 'email',    mapping, ALIASES['email'])
            phone    = resolve(row, 'phone',    mapping, ALIASES['phone'])
            document = resolve(row, 'document', mapping, ALIASES['document'])
            address  = resolve(row, 'address',  mapping, ALIASES['address'])
            city     = resolve(row, 'city',     mapping, ALIASES['city'])
            state    = resolve(row, 'state',    mapping, ALIASES['state'])
            notes    = resolve(row, 'notes',    mapping, ALIASES['notes'])

            # Verifica duplicata por nome exato
            existing = Client.query.filter_by(
                company_id=user.company_id, name=name
            ).first()

            if existing:
                # Verifica se outros campos diferem
                has_conflict = (
                    (email    and existing.email    and existing.email    != email)    or
                    (document and existing.document and existing.document != document) or
                    (phone    and existing.phone    and existing.phone    != phone)
                )
                if has_conflict:
                    duplicates.append({
                        'name':    name,
                        'message': f'Nome já existe com dados distintos (email/documento/telefone diferente)',
                        'row':     i,
                    })
                # Atualiza campos não vazios
                if email:    existing.email    = email
                if phone:    existing.phone    = phone
                if document: existing.document = document
                if address:  existing.address  = address
                if city:     existing.city     = city
                if state:    existing.state    = state
                if notes:    existing.notes    = notes
                updated += 1
            else:
                c = Client(
                    company_id = user.company_id,
                    name       = name,
                    email      = email   or None,
                    phone      = phone   or None,
                    document   = document or None,
                    address    = address  or None,
                    city       = city     or None,
                    state      = state    or None,
                    notes      = notes    or None,
                )
                db.session.add(c)
                imported += 1

        except Exception as e:
            errors.append({'row': i, 'field': '—', 'message': str(e)})
            skipped += 1

    return {
        'imported':             imported,
        'skipped':              skipped,
        'updated':              updated,
        'errors':               errors,
        'duplicates_notified':  duplicates,
    }


# ─────────────────────────────────────────────
# IMPORTAR PRODUTOS
# ─────────────────────────────────────────────

def import_products(rows, mapping, user):
    imported   = 0
    skipped    = 0
    updated    = 0
    errors     = []
    duplicates = []

    ALIASES = {
        'name':      ['Nome', 'nome', 'Name', 'Produto', 'Descrição'],
        'sku':       ['SKU', 'sku', 'Código', 'Cod', 'Ref', 'Referência'],
        'type':      ['Tipo', 'tipo', 'Type'],
        'category':  ['Categoria', 'categoria', 'Category'],
        'price':     ['Preço de Venda', 'preco_venda', 'Preço', 'Price', 'Valor Venda'],
        'cost':      ['Custo', 'custo', 'Cost', 'Valor Custo'],
        'stock_qty': ['Estoque', 'estoque', 'Stock', 'Qtd', 'Quantidade'],
        'stock_min': ['Estoque Mínimo', 'estoque_min', 'Min Stock', 'Qtd Mínima'],
        'unit':      ['Unidade', 'unidade', 'Unit', 'Un'],
        'description': ['Descrição', 'descricao', 'Description', 'Obs'],
    }

    for i, row in enumerate(rows, start=2):
        try:
            name = resolve(row, 'name', mapping, ALIASES['name'])
            if not name:
                errors.append({'row': i, 'field': 'Nome', 'message': 'Nome obrigatório'})
                skipped += 1
                continue

            sku         = resolve(row, 'sku',         mapping, ALIASES['sku'])         or None
            p_type      = resolve(row, 'type',        mapping, ALIASES['type'])        or 'produto'
            category    = resolve(row, 'category',    mapping, ALIASES['category'])    or 'Importado'
            price       = safe_float(resolve(row, 'price',     mapping, ALIASES['price']))
            cost        = safe_float(resolve(row, 'cost',      mapping, ALIASES['cost']))
            stock_qty   = int(safe_float(resolve(row, 'stock_qty', mapping, ALIASES['stock_qty'])))
            stock_min   = int(safe_float(resolve(row, 'stock_min', mapping, ALIASES['stock_min'])))
            unit        = resolve(row, 'unit',        mapping, ALIASES['unit'])        or 'un'
            description = resolve(row, 'description', mapping, ALIASES['description']) or None

            # Verifica duplicata por SKU (se tiver) ou nome
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

                # Registra movimentação de estoque se mudou
                if stock_qty and stock_qty != (existing.stock_qty or 0):
                    mv = StockMovement(
                        company_id  = user.company_id,
                        product_id  = existing.id,
                        type        = 'ajuste',
                        quantity    = stock_qty,
                        notes       = 'Ajuste via importação CSV',
                    )
                    db.session.add(mv)
            else:
                p = Product(
                    company_id  = user.company_id,
                    name        = name,
                    sku         = sku,
                    type        = p_type.lower(),
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

                # StockMovement inicial
                if stock_qty > 0:
                    mv = StockMovement(
                        company_id = user.company_id,
                        product_id = None,  # será preenchido após flush
                        type       = 'entrada',
                        quantity   = stock_qty,
                        notes      = 'Estoque inicial via importação CSV',
                    )
                    db.session.flush()
                    mv.product_id = p.id
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