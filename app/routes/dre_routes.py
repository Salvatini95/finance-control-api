from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Transaction, User, Company
from datetime import datetime, date
from collections import defaultdict

dre_bp = Blueprint('dre', __name__)


def _get_user(user_id):
    return User.query.get(int(user_id))


def _fmt_brl(value):
    """Formata valor para string BRL."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


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
        df  = date(ano, mes, 1)
        # último dia do mês
        if mes == 12:
            dt = date(ano + 1, 1, 1)
        else:
            dt = date(ano, mes + 1, 1)
        from datetime import timedelta
        dt = dt - timedelta(days=1)
        meses_pt = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                    'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
        label = f"{meses_pt[mes-1]}/{ano}"
        return df, dt, label

    if periodo == 'trimestre':
        tri = int(trimestre) if trimestre else ((today.month - 1) // 3 + 1)
        mes_inicio = (tri - 1) * 3 + 1
        mes_fim    = tri * 3
        df  = date(ano, mes_inicio, 1)
        if mes_fim == 12:
            dt = date(ano + 1, 1, 1)
        else:
            dt = date(ano, mes_fim + 1, 1)
        from datetime import timedelta
        dt = dt - timedelta(days=1)
        label = f"{tri}º Trimestre/{ano}"
        return df, dt, label

    # padrão: ano completo
    df    = date(ano, 1, 1)
    dt    = date(ano, 12, 31)
    label = f"Ano {ano}"
    return df, dt, label


def _categorize(transactions):
    """
    Separa transações em grupos do DRE:
    - receita_operacional: Vendas, Serviços Prestados, Consultoria
    - outras_receitas: demais income
    - custo_produtos: Fornecedores (CMV)
    - despesas_operacionais: Salários, Aluguel, Marketing, etc.
    - despesas_financeiras: Impostos, multas, juros
    - outras_despesas: demais expense
    """
    grupos = {
        'receita_operacional': [],
        'outras_receitas':     [],
        'custo_produtos':      [],
        'despesas_operacionais': [],
        'despesas_financeiras':  [],
        'outras_despesas':       [],
    }

    CAT_RECEITA_OP   = {'vendas', 'serviços prestados', 'serviços', 'consultoria', 'serviços prestados'}
    CAT_CMV          = {'fornecedores', 'custo', 'cmv', 'custo de mercadoria', 'estoque'}
    CAT_DESP_FIN     = {'impostos', 'imposto', 'juros', 'multas', 'taxas financeiras', 'financeiro'}
    CAT_DESP_OP      = {'salários', 'salario', 'aluguel', 'marketing', 'equipamentos',
                        'serviços', 'logística', 'logistica', 'suprimentos',
                        'utilidades', 'energia', 'internet', 'telefone'}

    for t in transactions:
        cat = (t.category or '').lower().strip()

        if t.type == 'income':
            if any(c in cat for c in CAT_RECEITA_OP) or cat in CAT_RECEITA_OP:
                grupos['receita_operacional'].append(t)
            else:
                grupos['outras_receitas'].append(t)
        else:
            if any(c in cat for c in CAT_CMV) or cat in CAT_CMV:
                grupos['custo_produtos'].append(t)
            elif any(c in cat for c in CAT_DESP_FIN) or cat in CAT_DESP_FIN:
                grupos['despesas_financeiras'].append(t)
            elif any(c in cat for c in CAT_DESP_OP) or cat in CAT_DESP_OP:
                grupos['despesas_operacionais'].append(t)
            else:
                grupos['outras_despesas'].append(t)

    return grupos


def _sum_by_category(transactions):
    """Agrupa e soma por categoria."""
    totais = defaultdict(float)
    for t in transactions:
        cat = t.category or 'Sem categoria'
        totais[cat] += t.amount
    return [{'categoria': k, 'valor': round(v, 2)} for k, v in sorted(totais.items(), key=lambda x: -x[1])]


def _build_dre(grupos, label_periodo, company_name, company_logo):
    """Monta a estrutura completa do DRE."""

    def total(lst):
        return round(sum(t.amount for t in lst), 2)

    receita_bruta      = total(grupos['receita_operacional'])
    outras_receitas    = total(grupos['outras_receitas'])
    cmv                = total(grupos['custo_produtos'])
    desp_operacionais  = total(grupos['despesas_operacionais'])
    desp_financeiras   = total(grupos['despesas_financeiras'])
    outras_despesas    = total(grupos['outras_despesas'])

    lucro_bruto        = round(receita_bruta - cmv, 2)
    resultado_operacional = round(lucro_bruto - desp_operacionais, 2)
    lucro_antes_ir     = round(resultado_operacional + outras_receitas - desp_financeiras, 2)
    lucro_liquido      = round(lucro_antes_ir - outras_despesas, 2)

    total_receitas     = round(receita_bruta + outras_receitas, 2)
    total_despesas     = round(cmv + desp_operacionais + desp_financeiras + outras_despesas, 2)

    # Margens
    margem_bruta       = round((lucro_bruto / receita_bruta * 100), 2) if receita_bruta else 0
    margem_operacional = round((resultado_operacional / receita_bruta * 100), 2) if receita_bruta else 0
    margem_liquida     = round((lucro_liquido / receita_bruta * 100), 2) if receita_bruta else 0

    return {
        'periodo':      label_periodo,
        'emitido_em':   datetime.now().strftime('%d/%m/%Y às %H:%M'),
        'company_name': company_name,
        'company_logo': company_logo,

        # ── ESTRUTURA DO DRE ──────────────────────────────
        'dre': [
            {
                'titulo':     '(+) Receita Operacional Bruta',
                'valor':      receita_bruta,
                'tipo':       'receita',
                'nivel':      1,
                'detalhe':    _sum_by_category(grupos['receita_operacional']),
            },
            {
                'titulo':     '(-) Custo das Mercadorias/Serviços (CMV/CSV)',
                'valor':      cmv,
                'tipo':       'deducao',
                'nivel':      1,
                'detalhe':    _sum_by_category(grupos['custo_produtos']),
            },
            {
                'titulo':     '(=) Lucro Bruto',
                'valor':      lucro_bruto,
                'tipo':       'resultado',
                'nivel':      1,
                'detalhe':    [],
                'margem':     margem_bruta,
            },
            {
                'titulo':     '(-) Despesas Operacionais',
                'valor':      desp_operacionais,
                'tipo':       'deducao',
                'nivel':      1,
                'detalhe':    _sum_by_category(grupos['despesas_operacionais']),
            },
            {
                'titulo':     '(=) Resultado Operacional (EBIT)',
                'valor':      resultado_operacional,
                'tipo':       'resultado',
                'nivel':      1,
                'detalhe':    [],
                'margem':     margem_operacional,
            },
            {
                'titulo':     '(+) Outras Receitas',
                'valor':      outras_receitas,
                'tipo':       'receita',
                'nivel':      1,
                'detalhe':    _sum_by_category(grupos['outras_receitas']),
            },
            {
                'titulo':     '(-) Despesas Financeiras',
                'valor':      desp_financeiras,
                'tipo':       'deducao',
                'nivel':      1,
                'detalhe':    _sum_by_category(grupos['despesas_financeiras']),
            },
            {
                'titulo':     '(=) Lucro Antes do IR (LAIR)',
                'valor':      lucro_antes_ir,
                'tipo':       'resultado',
                'nivel':      1,
                'detalhe':    [],
            },
            {
                'titulo':     '(-) Outras Despesas / Deduções',
                'valor':      outras_despesas,
                'tipo':       'deducao',
                'nivel':      1,
                'detalhe':    _sum_by_category(grupos['outras_despesas']),
            },
            {
                'titulo':     '(=) LUCRO LÍQUIDO DO PERÍODO',
                'valor':      lucro_liquido,
                'tipo':       'lucro_liquido',
                'nivel':      1,
                'detalhe':    [],
                'margem':     margem_liquida,
            },
        ],

        # ── INDICADORES ───────────────────────────────────
        'indicadores': {
            'receita_bruta':         receita_bruta,
            'outras_receitas':       outras_receitas,
            'total_receitas':        total_receitas,
            'cmv':                   cmv,
            'desp_operacionais':     desp_operacionais,
            'desp_financeiras':      desp_financeiras,
            'outras_despesas':       outras_despesas,
            'total_despesas':        total_despesas,
            'lucro_bruto':           lucro_bruto,
            'resultado_operacional': resultado_operacional,
            'lucro_antes_ir':        lucro_antes_ir,
            'lucro_liquido':         lucro_liquido,
            'margem_bruta':          margem_bruta,
            'margem_operacional':    margem_operacional,
            'margem_liquida':        margem_liquida,
            'saldo_periodo':         round(total_receitas - total_despesas, 2),
        },

        # ── TOTAIS DE TRANSAÇÕES ──────────────────────────
        'total_transacoes': sum(len(v) for v in grupos.values()),
    }


# ─────────────────────────────────────────────
# ENDPOINT PRINCIPAL
# ─────────────────────────────────────────────

@dre_bp.route('/dre', methods=['GET'])
@jwt_required()
def get_dre():
    user = _get_user(get_jwt_identity())

    # ── Parâmetros de filtro ──
    periodo     = request.args.get('periodo', 'ano')       # mes | trimestre | ano | personalizado
    ano         = request.args.get('ano')
    mes         = request.args.get('mes')
    trimestre   = request.args.get('trimestre')
    data_inicio = request.args.get('data_inicio')
    data_fim    = request.args.get('data_fim')

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

    # filtra por string de data (formato yyyy-mm-dd)
    date_from_str = date_from.strftime('%Y-%m-%d')
    date_to_str   = date_to.strftime('%Y-%m-%d')

    transactions = query.filter(
        Transaction.date >= date_from_str,
        Transaction.date <= date_to_str,
    ).all()

    # ── Dados da empresa ──
    company_name = localStorage_name = user.company_name or 'Minha Empresa'
    company_logo = None
    if user.company_id:
        company = Company.query.get(user.company_id)
        if company:
            company_name = company.name
            company_logo = company.logo

    # ── Monta DRE ──
    grupos = _categorize(transactions)
    dre    = _build_dre(grupos, label, company_name, company_logo)

    dre['filtros'] = {
        'periodo':     periodo,
        'date_from':   date_from_str,
        'date_to':     date_to_str,
        'ano':         ano,
        'mes':         mes,
        'trimestre':   trimestre,
    }

    return jsonify(dre), 200


# ─────────────────────────────────────────────
# ENDPOINT ANOS DISPONÍVEIS (para o filtro)
# ─────────────────────────────────────────────

@dre_bp.route('/dre/anos', methods=['GET'])
@jwt_required()
def get_anos_disponiveis():
    user = _get_user(get_jwt_identity())

    if user.company_id:
        transactions = Transaction.query.filter_by(company_id=user.company_id).all()
    else:
        transactions = Transaction.query.filter_by(user_id=user.id).all()

    anos = sorted(set(
        t.date[:4] for t in transactions if t.date and len(t.date) >= 4
    ), reverse=True)

    return jsonify({'anos': anos or [str(date.today().year)]}), 200
