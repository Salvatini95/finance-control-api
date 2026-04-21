from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Transaction, User, Company
from datetime import datetime, date, timedelta
from collections import defaultdict

cashflow_bp = Blueprint('cashflow', __name__)


def _get_user(user_id):
    return User.query.get(int(user_id))


def _parse_date(date_str):
    if not date_str:
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except Exception:
            continue
    return None


def _get_date_range(periodo, ano, mes, trimestre, data_inicio, data_fim):
    """Retorna (date_from, date_to, label) baseado nos parâmetros."""
    today = date.today()

    if data_inicio and data_fim:
        df = _parse_date(data_inicio)
        dt = _parse_date(data_fim)
        label = f"{df.strftime('%d/%m/%Y')} a {dt.strftime('%d/%m/%Y')}"
        return df, dt, label

    ano = int(ano) if ano else today.year

    if periodo == 'mes':
        mes = int(mes) if mes else today.month
        df = date(ano, mes, 1)
        if mes == 12:
            dt = date(ano + 1, 1, 1) - timedelta(days=1)
        else:
            dt = date(ano, mes + 1, 1) - timedelta(days=1)
        meses_pt = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                    'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
        label = f"{meses_pt[mes-1]}/{ano}"
        return df, dt, label

    if periodo == 'trimestre':
        tri = int(trimestre) if trimestre else ((today.month - 1) // 3 + 1)
        mes_inicio = (tri - 1) * 3 + 1
        mes_fim    = tri * 3
        df = date(ano, mes_inicio, 1)
        if mes_fim == 12:
            dt = date(ano + 1, 1, 1) - timedelta(days=1)
        else:
            dt = date(ano, mes_fim + 1, 1) - timedelta(days=1)
        label = f"{tri}º Trimestre/{ano}"
        return df, dt, label

    # ano completo
    df    = date(ano, 1, 1)
    dt    = date(ano, 12, 31)
    label = f"Ano {ano}"
    return df, dt, label


def _build_daily(transactions, date_from, date_to):
    """Agrupa transações por dia."""
    by_day = defaultdict(lambda: {'income': 0.0, 'expense': 0.0})
    for t in transactions:
        d = t.date[:10] if t.date else None
        if not d:
            continue
        if t.type == 'income':
            by_day[d]['income'] += t.amount
        else:
            by_day[d]['expense'] += t.amount

    rows = []
    current = date_from
    while current <= date_to:
        key = current.strftime('%Y-%m-%d')
        income  = round(by_day[key]['income'],  2)
        expense = round(by_day[key]['expense'], 2)
        rows.append({
            'date':       key,
            'label':      current.strftime('%d/%m/%Y'),
            'weekday':    ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'][current.weekday()],
            'income':     income,
            'expense':    expense,
            'net':        round(income - expense, 2),
            'has_data':   income > 0 or expense > 0,
        })
        current += timedelta(days=1)

    return rows


def _build_weekly(transactions, date_from, date_to):
    """Agrupa transações por semana."""
    by_week = defaultdict(lambda: {'income': 0.0, 'expense': 0.0, 'label': ''})

    for t in transactions:
        d = _parse_date(t.date[:10]) if t.date else None
        if not d:
            continue
        # segunda-feira da semana
        monday  = d - timedelta(days=d.weekday())
        sunday  = monday + timedelta(days=6)
        wkey    = monday.strftime('%Y-%m-%d')
        wlabel  = f"{monday.strftime('%d/%m')} – {sunday.strftime('%d/%m/%Y')}"
        by_week[wkey]['label']  = wlabel
        if t.type == 'income':
            by_week[wkey]['income']  += t.amount
        else:
            by_week[wkey]['expense'] += t.amount

    # garante semanas no intervalo mesmo sem dados
    rows = []
    current = date_from - timedelta(days=date_from.weekday())  # começa na segunda
    seen = set()
    while current <= date_to:
        key    = current.strftime('%Y-%m-%d')
        sunday = current + timedelta(days=6)
        if key not in seen:
            seen.add(key)
            income  = round(by_week[key]['income'],  2)
            expense = round(by_week[key]['expense'], 2)
            rows.append({
                'date':    key,
                'label':   by_week[key]['label'] or f"{current.strftime('%d/%m')} – {sunday.strftime('%d/%m/%Y')}",
                'income':  income,
                'expense': expense,
                'net':     round(income - expense, 2),
                'has_data': income > 0 or expense > 0,
            })
        current += timedelta(days=7)

    return rows


def _build_monthly(transactions):
    """Agrupa transações por mês."""
    meses_pt = ['Jan','Fev','Mar','Abr','Mai','Jun',
                'Jul','Ago','Set','Out','Nov','Dez']
    by_month = defaultdict(lambda: {'income': 0.0, 'expense': 0.0})

    for t in transactions:
        d = _parse_date(t.date[:10]) if t.date else None
        if not d:
            continue
        mkey = d.strftime('%Y-%m')
        if t.type == 'income':
            by_month[mkey]['income']  += t.amount
        else:
            by_month[mkey]['expense'] += t.amount

    rows = []
    for mkey in sorted(by_month.keys()):
        y, m = map(int, mkey.split('-'))
        income  = round(by_month[mkey]['income'],  2)
        expense = round(by_month[mkey]['expense'], 2)
        rows.append({
            'date':    mkey,
            'label':   f"{meses_pt[m-1]}/{y}",
            'income':  income,
            'expense': expense,
            'net':     round(income - expense, 2),
            'has_data': True,
        })

    return rows


# ─────────────────────────────────────────────
# ENDPOINT PRINCIPAL
# ─────────────────────────────────────────────

@cashflow_bp.route('/cashflow', methods=['GET'])
@jwt_required()
def get_cashflow():
    user = _get_user(get_jwt_identity())

    # ── Parâmetros ──
    periodo      = request.args.get('periodo', 'mes')
    ano          = request.args.get('ano')
    mes          = request.args.get('mes')
    trimestre    = request.args.get('trimestre')
    data_inicio  = request.args.get('data_inicio')
    data_fim     = request.args.get('data_fim')
    agrupamento  = request.args.get('agrupamento', 'daily')  # daily | weekly | monthly

    date_from, date_to, label = _get_date_range(
        periodo, ano, mes, trimestre, data_inicio, data_fim
    )

    if not date_from or not date_to:
        return jsonify({'error': 'Período inválido'}), 400

    # ── Busca transações ──
    if user.company_id:
        query = Transaction.query.filter_by(company_id=user.company_id)
    else:
        query = Transaction.query.filter_by(user_id=user.id)

    date_from_str = date_from.strftime('%Y-%m-%d')
    date_to_str   = date_to.strftime('%Y-%m-%d')

    transactions = query.filter(
        Transaction.date >= date_from_str,
        Transaction.date <= date_to_str,
    ).order_by(Transaction.date).all()

    # ── Saldo inicial (tudo ANTES do período) ──
    prev_transactions = query.filter(
        Transaction.date < date_from_str,
    ).all()

    saldo_inicial = round(
        sum(t.amount if t.type == 'income' else -t.amount for t in prev_transactions), 2
    )

    # ── Totais do período ──
    total_income  = round(sum(t.amount for t in transactions if t.type == 'income'),  2)
    total_expense = round(sum(t.amount for t in transactions if t.type == 'expense'), 2)
    saldo_periodo = round(total_income - total_expense, 2)
    saldo_final   = round(saldo_inicial + saldo_periodo, 2)

    # ── Agrupamento ──
    if agrupamento == 'weekly':
        rows = _build_weekly(transactions, date_from, date_to)
    elif agrupamento == 'monthly':
        rows = _build_monthly(transactions)
    else:
        rows = _build_daily(transactions, date_from, date_to)

    # ── Saldo acumulado linha a linha ──
    acumulado = saldo_inicial
    for row in rows:
        acumulado = round(acumulado + row['net'], 2)
        row['saldo_acumulado'] = acumulado

    # ── Dados da empresa ──
    company_name = user.company_name or 'Minha Empresa'
    company_logo = None
    if user.company_id:
        company = Company.query.get(user.company_id)
        if company:
            company_name = company.name
            company_logo = company.logo

    # ── Indicadores extra ──
    dias_positivos = sum(1 for r in rows if r['net'] > 0)
    dias_negativos = sum(1 for r in rows if r['net'] < 0)
    maior_entrada  = max((r['income']  for r in rows), default=0)
    maior_saida    = max((r['expense'] for r in rows), default=0)
    media_entrada  = round(total_income  / len(rows), 2) if rows else 0
    media_saida    = round(total_expense / len(rows), 2) if rows else 0

    return jsonify({
        'periodo':       label,
        'agrupamento':   agrupamento,
        'emitido_em':    datetime.now().strftime('%d/%m/%Y às %H:%M'),
        'company_name':  company_name,
        'company_logo':  company_logo,
        'saldo_inicial': saldo_inicial,
        'saldo_final':   saldo_final,
        'saldo_periodo': saldo_periodo,
        'total_income':  total_income,
        'total_expense': total_expense,
        'rows':          rows,
        'indicadores': {
            'dias_positivos': dias_positivos,
            'dias_negativos': dias_negativos,
            'maior_entrada':  maior_entrada,
            'maior_saida':    maior_saida,
            'media_entrada':  media_entrada,
            'media_saida':    media_saida,
            'total_linhas':   len(rows),
            'total_transacoes': len(transactions),
        },
        'filtros': {
            'periodo':    periodo,
            'date_from':  date_from_str,
            'date_to':    date_to_str,
            'agrupamento': agrupamento,
        },
    }), 200


# ─────────────────────────────────────────────
# ANOS DISPONÍVEIS
# ─────────────────────────────────────────────

@cashflow_bp.route('/cashflow/anos', methods=['GET'])
@jwt_required()
def get_anos_cashflow():
    user = _get_user(get_jwt_identity())

    if user.company_id:
        transactions = Transaction.query.filter_by(company_id=user.company_id).all()
    else:
        transactions = Transaction.query.filter_by(user_id=user.id).all()

    anos = sorted(set(
        t.date[:4] for t in transactions if t.date and len(t.date) >= 4
    ), reverse=True)

    return jsonify({'anos': anos or [str(date.today().year)]}), 200