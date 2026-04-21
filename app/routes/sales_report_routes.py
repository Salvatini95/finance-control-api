from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Order, User, Company
from datetime import datetime, date, timedelta
from collections import defaultdict
import json

sales_report_bp = Blueprint('sales_report', __name__)


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
        a = _parse_date(di); b = _parse_date(df_)
        return a, b, f"{a.strftime('%d/%m/%Y')} a {b.strftime('%d/%m/%Y')}"
    ano = int(ano) if ano else today.year
    if periodo == 'mes':
        mes = int(mes) if mes else today.month
        a = date(ano, mes, 1)
        b = date(ano, mes+1, 1)-timedelta(days=1) if mes<12 else date(ano,12,31)
        meses=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
        return a, b, f"{meses[mes-1]}/{ano}"
    if periodo == 'trimestre':
        tri=int(trimestre) if trimestre else ((today.month-1)//3+1)
        mi=(tri-1)*3+1; mf=tri*3
        a=date(ano,mi,1); b=date(ano,mf+1,1)-timedelta(days=1) if mf<12 else date(ano,12,31)
        return a, b, f"{tri}º Trimestre/{ano}"
    return date(ano,1,1), date(ano,12,31), f"Ano {ano}"


@sales_report_bp.route('/orders/report', methods=['GET'])
@jwt_required()
def get_sales_report():
    user = _get_user(get_jwt_identity())
    periodo=request.args.get('periodo','mes'); ano=request.args.get('ano')
    mes=request.args.get('mes'); tri=request.args.get('trimestre')
    di=request.args.get('data_inicio'); df_=request.args.get('data_fim')
    vid=request.args.get('vendedor_id'); cid=request.args.get('cliente_id')
    st=request.args.get('status','all')

    date_from, date_to, label = _date_range(periodo, ano, mes, tri, di, df_)
    dfs=date_from.strftime('%Y-%m-%d'); dts=date_to.strftime('%Y-%m-%d')

    q = Order.query.filter_by(company_id=user.company_id) if user.company_id else Order.query.filter_by(user_id=user.id)
    orders = q.filter(Order.created_at>=dfs, Order.created_at<=dts).order_by(Order.created_at.desc()).all()

    if vid and vid!='all': orders=[o for o in orders if str(o.user_id)==str(vid)]
    if cid and cid!='all': orders=[o for o in orders if str(o.client_id)==str(cid)]
    if st!='all': orders=[o for o in orders if o.status==st]

    data=[]
    for o in orders:
        items=json.loads(o.items_json or '[]')
        data.append({'id':o.id,'number':o.number,'doc_type':'OS' if o.number.startswith('OS-') else 'PED',
            'status':o.status,'client_name':o.client.name if o.client else '—','client_id':o.client_id,
            'user_id':o.user_id,'subtotal':o.subtotal,'discount':o.discount,'total':o.total,
            'created_at':o.created_at or '—','finished_at':o.finished_at,'origin':o.origin,
            'items_count':len(items),'payment_terms':o.payment_terms or '—'})

    done=[o for o in data if o['status']=='done']
    faturado=round(sum(o['total'] for o in done),2)
    ped_total=round(sum(o['total'] for o in done if o['doc_type']=='PED'),2)
    os_total =round(sum(o['total'] for o in done if o['doc_type']=='OS'),2)

    by_client=defaultdict(lambda:{'count':0,'total':0.0})
    for o in done:
        by_client[o['client_name']]['count']+=1
        by_client[o['client_name']]['total']+=o['total']
    top=sorted([{'name':k,'count':v['count'],'total':round(v['total'],2)} for k,v in by_client.items()],key=lambda x:-x['total'])[:10]

    company_name=user.company_name or 'Minha Empresa'; company_logo=None
    if user.company_id:
        c=Company.query.get(user.company_id)
        if c: company_name=c.name; company_logo=c.logo

    return jsonify({'periodo':label,'emitido_em':datetime.now().strftime('%d/%m/%Y às %H:%M'),
        'company_name':company_name,'company_logo':company_logo,'orders':data,'top_clientes':top,
        'totais':{'total_ordens':len(data),'total_concluidas':len(done),'total_faturado':faturado,
            'total_pedidos':ped_total,'total_os':os_total,
            'ticket_medio':round(faturado/len(done),2) if done else 0,
            'total_abertas':len([o for o in data if o['status']=='open'])},
        'filtros':{'periodo':periodo,'date_from':dfs,'date_to':dts,'status':st}}), 200