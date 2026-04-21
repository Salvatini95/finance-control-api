from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Transaction, User, Company
from datetime import datetime, date, timedelta
from collections import defaultdict

dre_bp = Blueprint('dre', __name__)


def _get_user(uid): return User.query.get(int(uid))


def _parse_date(s):
    if not s: return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
        try: return datetime.strptime(s, fmt).date()
        except: continue
    return None


def _normalize_date(d):
    """Garante que uma string de data vire date(), independente do formato."""
    if not d: return None
    if isinstance(d, date): return d
    return _parse_date(str(d))


def _get_date_range(periodo, ano, mes, trimestre, data_inicio, data_fim):
    today = date.today()
    if data_inicio and data_fim:
        a = _parse_date(data_inicio); b = _parse_date(data_fim)
        return a, b, f"{a.strftime('%d/%m/%Y')} a {b.strftime('%d/%m/%Y')}"
    ano = int(ano) if ano else today.year
    if periodo == 'mes':
        mes = int(mes) if mes else today.month
        a = date(ano, mes, 1)
        b = date(ano, mes+1, 1) - timedelta(days=1) if mes < 12 else date(ano, 12, 31)
        meses = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                 'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
        return a, b, f"{meses[mes-1]}/{ano}"
    if periodo == 'trimestre':
        tri = int(trimestre) if trimestre else ((today.month-1)//3+1)
        mi = (tri-1)*3+1; mf = tri*3
        a = date(ano, mi, 1)
        b = date(ano, mf+1, 1) - timedelta(days=1) if mf < 12 else date(ano, 12, 31)
        return a, b, f"{tri}º Trimestre/{ano}"
    return date(ano,1,1), date(ano,12,31), f"Ano {ano}"


def _sum_by_cat(transactions):
    totais = defaultdict(float)
    for t in transactions:
        totais[t.category or 'Sem categoria'] += t.amount
    return sorted([{'nome': k, 'valor': round(v,2)} for k,v in totais.items()], key=lambda x: -x['valor'])


def _categorize(transactions):
    grupos = {k:[] for k in ['receita_op','outras_receitas','cmv',
                               'desp_op','desp_fin','outras_desp']}
    CAT_REC_OP  = {'vendas','serviços prestados','serviços','consultoria'}
    CAT_CMV     = {'fornecedores','custo','cmv','custo de mercadoria','estoque'}
    CAT_DESP_FIN= {'impostos','imposto','juros','multas','taxas financeiras','financeiro'}
    CAT_DESP_OP = {'salários','salario','aluguel','marketing','equipamentos',
                   'logística','logistica','suprimentos','utilidades',
                   'energia','internet','telefone'}
    for t in transactions:
        cat = (t.category or '').lower().strip()
        if t.type == 'income':
            if cat in CAT_REC_OP or any(c in cat for c in CAT_REC_OP):
                grupos['receita_op'].append(t)
            else:
                grupos['outras_receitas'].append(t)
        else:
            if cat in CAT_CMV or any(c in cat for c in CAT_CMV):
                grupos['cmv'].append(t)
            elif cat in CAT_DESP_FIN or any(c in cat for c in CAT_DESP_FIN):
                grupos['desp_fin'].append(t)
            elif cat in CAT_DESP_OP or any(c in cat for c in CAT_DESP_OP):
                grupos['desp_op'].append(t)
            else:
                grupos['outras_desp'].append(t)
    return grupos


@dre_bp.route('/dre', methods=['GET'])
@jwt_required()
def get_dre():
    user = _get_user(get_jwt_identity())
    periodo   = request.args.get('periodo', 'ano')
    ano       = request.args.get('ano')
    mes       = request.args.get('mes')
    trimestre = request.args.get('trimestre')
    di        = request.args.get('data_inicio')
    df_       = request.args.get('data_fim')

    date_from, date_to, label = _get_date_range(periodo, ano, mes, trimestre, di, df_)
    if not date_from or not date_to:
        return jsonify({'error': 'Período inválido'}), 400

    # ── busca transações da empresa ──
    q = Transaction.query.filter_by(company_id=user.company_id) if user.company_id \
        else Transaction.query.filter_by(user_id=user.id)
    all_txs = q.all()

    # ── filtro de data robusto: normaliza cada registro individualmente ──
    transactions = []
    for t in all_txs:
        d = _normalize_date(t.date)
        if d and date_from <= d <= date_to:
            transactions.append(t)

    # ── empresa ──
    company_name = user.company_name or 'Minha Empresa'
    company_logo = None
    if user.company_id:
        c = Company.query.get(user.company_id)
        if c: company_name = c.name; company_logo = c.logo

    # ── monta DRE ──
    g = _categorize(transactions)
    T = lambda lst: round(sum(t.amount for t in lst), 2)

    receita_bruta       = T(g['receita_op'])
    outras_receitas     = T(g['outras_receitas'])
    cmv                 = T(g['cmv'])
    desp_op             = T(g['desp_op'])
    desp_fin            = T(g['desp_fin'])
    outras_desp         = T(g['outras_desp'])

    lucro_bruto         = round(receita_bruta - cmv, 2)
    resultado_op        = round(lucro_bruto - desp_op, 2)
    lucro_antes_ir      = round(resultado_op + outras_receitas - desp_fin, 2)
    lucro_liquido       = round(lucro_antes_ir - outras_desp, 2)
    total_receitas      = round(receita_bruta + outras_receitas, 2)
    total_despesas      = round(cmv + desp_op + desp_fin + outras_desp, 2)

    pct = lambda v: round(v / receita_bruta * 100, 2) if receita_bruta else 0

    # ── estrutura de secoes para o frontend ──
    secoes = [
        {
            'nome':  'Receitas',
            'total': total_receitas,
            'items': [
                {'nome': '(+) Receita Operacional Bruta', 'valor': receita_bruta,   'pct_receita': pct(receita_bruta),   'children': _sum_by_cat(g['receita_op'])},
                {'nome': '(+) Outras Receitas',            'valor': outras_receitas, 'pct_receita': pct(outras_receitas), 'children': _sum_by_cat(g['outras_receitas'])},
            ]
        },
        {
            'nome':  'Custos e Despesas',
            'total': -total_despesas,
            'items': [
                {'nome': '(-) CMV / CSV',                  'valor': -cmv,        'pct_receita': pct(cmv),      'children': _sum_by_cat(g['cmv'])},
                {'nome': '(-) Despesas Operacionais',      'valor': -desp_op,    'pct_receita': pct(desp_op),  'children': _sum_by_cat(g['desp_op'])},
                {'nome': '(-) Despesas Financeiras',       'valor': -desp_fin,   'pct_receita': pct(desp_fin), 'children': _sum_by_cat(g['desp_fin'])},
                {'nome': '(-) Outras Despesas',            'valor': -outras_desp,'pct_receita': pct(outras_desp),'children': _sum_by_cat(g['outras_desp'])},
            ]
        },
        {
            'nome':  'Resultados',
            'total': lucro_liquido,
            'items': [
                {'nome': '(=) Lucro Bruto',             'valor': lucro_bruto,    'pct_receita': pct(lucro_bruto),    'children': []},
                {'nome': '(=) Resultado Operacional',   'valor': resultado_op,   'pct_receita': pct(resultado_op),   'children': []},
                {'nome': '(=) Lucro Antes do IR (LAIR)','valor': lucro_antes_ir, 'pct_receita': pct(lucro_antes_ir), 'children': []},
                {'nome': '(=) LUCRO LÍQUIDO',           'valor': lucro_liquido,  'pct_receita': pct(lucro_liquido),  'children': []},
            ]
        },
    ]

    return jsonify({
        'periodo':        label,
        'emitido_em':     datetime.now().strftime('%d/%m/%Y às %H:%M'),
        'company_name':   company_name,
        'company_logo':   company_logo,
        # campos diretos que o Reports.jsx lê nos KPI cards
        'receita_bruta':  receita_bruta,
        'total_despesas': total_despesas,
        'lucro_liquido':  lucro_liquido,
        'margem_liquida': pct(lucro_liquido),
        # seções expansíveis
        'secoes':         secoes,
        'total_transacoes': len(transactions),
        'filtros': {
            'periodo':   periodo,
            'date_from': date_from.strftime('%Y-%m-%d'),
            'date_to':   date_to.strftime('%Y-%m-%d'),
        },
    }), 200


@dre_bp.route('/dre/anos', methods=['GET'])
@jwt_required()
def get_anos_disponiveis():
    user = _get_user(get_jwt_identity())
    txs = Transaction.query.filter_by(company_id=user.company_id).all() if user.company_id \
          else Transaction.query.filter_by(user_id=user.id).all()
    anos = sorted(set(
        str(_normalize_date(t.date).year)
        for t in txs if _normalize_date(t.date)
    ), reverse=True)
    return jsonify({'anos': anos or [str(date.today().year)]}), 200