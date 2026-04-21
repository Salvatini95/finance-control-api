from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import StockMovement, Product, User, Company
from datetime import datetime, date, timedelta
from collections import defaultdict

stock_report_bp = Blueprint('stock_report', __name__)


def _get_user(uid): return User.query.get(int(uid))

def _parse_date(s):
    if not s: return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
        try: return datetime.strptime(s, fmt).date()
        except: continue
    return None

def _date_range(periodo, ano, mes, trimestre, di, df_):
    today = date.today()
    if di and df_:
        a=_parse_date(di); b=_parse_date(df_)
        return a, b, f"{a.strftime('%d/%m/%Y')} a {b.strftime('%d/%m/%Y')}"
    ano=int(ano) if ano else today.year
    if periodo=='mes':
        mes=int(mes) if mes else today.month
        a=date(ano,mes,1); b=date(ano,mes+1,1)-timedelta(days=1) if mes<12 else date(ano,12,31)
        meses=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
        return a, b, f"{meses[mes-1]}/{ano}"
    if periodo=='trimestre':
        tri=int(trimestre) if trimestre else ((today.month-1)//3+1)
        mi=(tri-1)*3+1; mf=tri*3
        a=date(ano,mi,1); b=date(ano,mf+1,1)-timedelta(days=1) if mf<12 else date(ano,12,31)
        return a, b, f"{tri}º Trimestre/{ano}"
    return date(ano,1,1), date(ano,12,31), f"Ano {ano}"


@stock_report_bp.route('/stock/report', methods=['GET'])
@jwt_required()
def get_stock_report():
    user=_get_user(get_jwt_identity())
    periodo=request.args.get('periodo','mes'); ano=request.args.get('ano')
    mes=request.args.get('mes'); tri=request.args.get('trimestre')
    di=request.args.get('data_inicio'); df_=request.args.get('data_fim')
    tipo=request.args.get('tipo','all')  # in | out | adjustment | all
    product_id=request.args.get('product_id')

    date_from, date_to, label = _date_range(periodo, ano, mes, tri, di, df_)
    dfs=date_from.strftime('%Y-%m-%d'); dts=date_to.strftime('%Y-%m-%d')

    company_id=user.company_id
    q = StockMovement.query
    if company_id:
        # filtra pelos produtos da empresa
        prod_ids=[p.id for p in Product.query.filter_by(company_id=company_id).all()]
        q=q.filter(StockMovement.product_id.in_(prod_ids))
    else:
        prod_ids=[p.id for p in Product.query.filter_by(user_id=user.id).all()]
        q=q.filter(StockMovement.product_id.in_(prod_ids))

    q=q.filter(StockMovement.created_at>=dfs, StockMovement.created_at<=dts)
    if tipo!='all': q=q.filter(StockMovement.type==tipo)
    if product_id and product_id!='all': q=q.filter(StockMovement.product_id==int(product_id))
    movements=q.order_by(StockMovement.created_at.desc()).all()

    # Produtos para lookup
    prods={p.id:p for p in Product.query.filter(Product.id.in_(prod_ids)).all()}

    data=[]
    for m in movements:
        p=prods.get(m.product_id)
        data.append({'id':m.id,'product_id':m.product_id,
            'product_name':p.name if p else '—','product_sku':p.sku if p else '—',
            'type':m.type,'quantity':m.quantity,'reason':m.reason or '—',
            'created_at':m.created_at.strftime('%d/%m/%Y %H:%M') if m.created_at else '—',
            'reference':getattr(m,'reference',None)})

    entradas=sum(m['quantity'] for m in data if m['type']=='in')
    saidas  =sum(m['quantity'] for m in data if m['type']=='out')
    ajustes =sum(m['quantity'] for m in data if m['type']=='adjustment')

    # Saldo atual dos produtos filtrados
    current_stock=[]
    target_ids=[int(product_id)] if product_id and product_id!='all' else prod_ids
    for pid in target_ids:
        p=prods.get(pid)
        if p: current_stock.append({'id':p.id,'name':p.name,'sku':p.sku or '—',
            'stock_qty':p.stock_qty,'stock_min':p.stock_min,'below_min':p.stock_qty<p.stock_min if p.stock_min else False})

    # Mais movimentados
    by_product=defaultdict(lambda:{'name':'—','sku':'—','entradas':0,'saidas':0})
    for m in data:
        by_product[m['product_id']]['name']=m['product_name']
        by_product[m['product_id']]['sku'] =m['product_sku']
        if m['type']=='in':  by_product[m['product_id']]['entradas']+=m['quantity']
        if m['type']=='out': by_product[m['product_id']]['saidas']  +=m['quantity']
    mais_movimentados=sorted(
        [{'product_id':k,'name':v['name'],'sku':v['sku'],'entradas':v['entradas'],'saidas':v['saidas'],'total':v['entradas']+v['saidas']} for k,v in by_product.items()],
        key=lambda x:-x['total'])[:10]

    company_name=user.company_name or 'Minha Empresa'; company_logo=None
    if company_id:
        c=Company.query.get(company_id)
        if c: company_name=c.name; company_logo=c.logo

    return jsonify({'periodo':label,'emitido_em':datetime.now().strftime('%d/%m/%Y às %H:%M'),
        'company_name':company_name,'company_logo':company_logo,
        'movements':data,'current_stock':current_stock,'mais_movimentados':mais_movimentados,
        'totais':{'total_movimentos':len(data),'total_entradas':entradas,'total_saidas':saidas,'total_ajustes':ajustes},
        'filtros':{'periodo':periodo,'date_from':dfs,'date_to':dts,'tipo':tipo,'product_id':product_id}}), 200