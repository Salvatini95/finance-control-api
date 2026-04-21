from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Bill, User, Company
from datetime import datetime, date, timedelta

bills_report_bp = Blueprint('bills_report', __name__)


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
    today = date.today()

    if data_inicio and data_fim:
        df = _parse_date(data_inicio)
        dt = _parse_date(data_fim)
        label = f"{df.strftime('%d/%m/%Y')} a {dt.strftime('%d/%m/%Y')}"
        return df, dt, label

    ano = int(ano) if ano else today.year

    if periodo == 'mes':
        mes = int(mes) if mes else today.month
        df  = date(ano, mes, 1)
        dt  = date(ano, mes + 1, 1) - timedelta(days=1) if mes < 12 else date(ano, 12, 31)
        meses_pt = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                    'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
        label = f"{meses_pt[mes-1]}/{ano}"
        return df, dt, label

    if periodo == 'trimestre':
        tri       = int(trimestre) if trimestre else ((today.month - 1) // 3 + 1)
        mes_inicio = (tri - 1) * 3 + 1
        mes_fim    = tri * 3
        df  = date(ano, mes_inicio, 1)
        dt  = date(ano, mes_fim + 1, 1) - timedelta(days=1) if mes_fim < 12 else date(ano, 12, 31)
        label = f"{tri}º Trimestre/{ano}"
        return df, dt, label

    df    = date(ano, 1, 1)
    dt    = date(ano, 12, 31)
    label = f"Ano {ano}"
    return df, dt, label


def _serialize_bill(b):
    return {
        'id':          b.id,
        'description': b.description or '—',
        'type':        b.type,
        'amount':      b.amount,
        'status':      b.status,
        'due_date':    b.due_date or '—',
        'paid_date':   b.paid_date or None,
        'category':    b.category or '—',
        'notes':       b.notes or '',
    }


@bills_report_bp.route('/bills/report', methods=['GET'])
@jwt_required()
def get_bills_report():
    user = _get_user(get_jwt_identity())

    # ── Parâmetros ──
    periodo    = request.args.get('periodo', 'mes')
    ano        = request.args.get('ano')
    mes        = request.args.get('mes')
    trimestre  = request.args.get('trimestre')
    data_inicio = request.args.get('data_inicio')
    data_fim    = request.args.get('data_fim')
    tipo        = request.args.get('tipo', 'all')  # all | payable | receivable

    date_from, date_to, label = _get_date_range(
        periodo, ano, mes, trimestre, data_inicio, data_fim
    )

    if not date_from or not date_to:
        return jsonify({'error': 'Período inválido'}), 400

    date_from_str = date_from.strftime('%Y-%m-%d')
    date_to_str   = date_to.strftime('%Y-%m-%d')
    today         = date.today()
    today_str     = today.strftime('%Y-%m-%d')

    # ── Query base ──
    if user.company_id:
        query = Bill.query.filter_by(company_id=user.company_id)
    else:
        query = Bill.query.filter_by(user_id=user.id)

    if tipo != 'all':
        query = query.filter_by(type=tipo)

    all_bills = query.all()

    # ── Seção 1: VENCIDAS (não pagas, vencimento <= hoje, dentro do período) ──
    vencidas = []
    for b in all_bills:
        if b.status == 'paid':
            continue
        if not b.due_date:
            continue
        due = _parse_date(b.due_date)
        if not due:
            continue
        if due <= today and date_from <= due <= date_to:
            days_late = (today - due).days
            s = _serialize_bill(b)
            s['days_late'] = days_late
            vencidas.append(s)

    vencidas.sort(key=lambda x: x['due_date'])

    # ── Seção 2: A VENCER (não pagas, vencimento > hoje) ──
    a_vencer_7  = []
    a_vencer_15 = []
    a_vencer_30 = []
    a_vencer_30_plus = []

    for b in all_bills:
        if b.status == 'paid':
            continue
        if not b.due_date:
            continue
        due = _parse_date(b.due_date)
        if not due or due <= today:
            continue
        days_until = (due - today).days
        s = _serialize_bill(b)
        s['days_until'] = days_until
        if days_until <= 7:
            a_vencer_7.append(s)
        elif days_until <= 15:
            a_vencer_15.append(s)
        elif days_until <= 30:
            a_vencer_30.append(s)
        else:
            a_vencer_30_plus.append(s)

    for lst in [a_vencer_7, a_vencer_15, a_vencer_30, a_vencer_30_plus]:
        lst.sort(key=lambda x: x['due_date'])

    # ── Seção 3: PAGAS no período (paid_date ou due_date dentro do range) ──
    pagas = []
    for b in all_bills:
        if b.status != 'paid':
            continue
        ref_date_str = b.paid_date or b.due_date
        if not ref_date_str:
            continue
        ref = _parse_date(ref_date_str)
        if not ref:
            continue
        if date_from <= ref <= date_to:
            pagas.append(_serialize_bill(b))

    pagas.sort(key=lambda x: x['paid_date'] or x['due_date'])

    # ── Totais ──
    def total(lst, t=None):
        if t:
            return round(sum(b['amount'] for b in lst if b['type'] == t), 2)
        return round(sum(b['amount'] for b in lst), 2)

    total_vencidas_pay = total(vencidas, 'payable')
    total_vencidas_rec = total(vencidas, 'receivable')
    total_a_vencer_pay = total(a_vencer_7 + a_vencer_15 + a_vencer_30 + a_vencer_30_plus, 'payable')
    total_a_vencer_rec = total(a_vencer_7 + a_vencer_15 + a_vencer_30 + a_vencer_30_plus, 'receivable')
    total_pagas_pay    = total(pagas, 'payable')
    total_pagas_rec    = total(pagas, 'receivable')

    # ── Dados da empresa ──
    company_name = user.company_name or 'Minha Empresa'
    company_logo = None
    if user.company_id:
        company = Company.query.get(user.company_id)
        if company:
            company_name = company.name
            company_logo = company.logo

    return jsonify({
        'periodo':      label,
        'emitido_em':   datetime.now().strftime('%d/%m/%Y às %H:%M'),
        'company_name': company_name,
        'company_logo': company_logo,
        'today':        today_str,
        'filtros': {
            'periodo':    periodo,
            'tipo':       tipo,
            'date_from':  date_from_str,
            'date_to':    date_to_str,
        },
        'secoes': {
            'vencidas':        vencidas,
            'a_vencer_7':      a_vencer_7,
            'a_vencer_15':     a_vencer_15,
            'a_vencer_30':     a_vencer_30,
            'a_vencer_30_plus': a_vencer_30_plus,
            'pagas':           pagas,
        },
        'totais': {
            'vencidas_payable':    total_vencidas_pay,
            'vencidas_receivable': total_vencidas_rec,
            'vencidas_total':      round(total_vencidas_pay + total_vencidas_rec, 2),
            'a_vencer_payable':    total_a_vencer_pay,
            'a_vencer_receivable': total_a_vencer_rec,
            'a_vencer_total':      round(total_a_vencer_pay + total_a_vencer_rec, 2),
            'pagas_payable':       total_pagas_pay,
            'pagas_receivable':    total_pagas_rec,
            'pagas_total':         round(total_pagas_pay + total_pagas_rec, 2),
            'total_contas':        len(vencidas) + len(a_vencer_7) + len(a_vencer_15) + len(a_vencer_30) + len(a_vencer_30_plus) + len(pagas),
        },
    }), 200


@bills_report_bp.route('/bills/report/anos', methods=['GET'])
@jwt_required()
def get_anos_bills():
    user = _get_user(get_jwt_identity())
    if user.company_id:
        bills = Bill.query.filter_by(company_id=user.company_id).all()
    else:
        bills = Bill.query.filter_by(user_id=user.id).all()

    anos = sorted(set(
        b.due_date[:4] for b in bills if b.due_date and len(b.due_date) >= 4
    ), reverse=True)

    return jsonify({'anos': anos or [str(date.today().year)]}), 200