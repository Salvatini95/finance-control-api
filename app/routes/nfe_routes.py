from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Order, Product, User
import json, requests, os

nfe_bp = Blueprint("nfe", __name__)

FOCUS_URL = "https://homologacao.focusnfe.com.br/v2"
FOCUS_TOKEN_SANDBOX = os.environ.get("FOCUS_TOKEN_SANDBOX", "66R3bCwxnRBMzyx4QFunliCN8C3GEww1")


def _get_user(user_id):
    return User.query.get(int(user_id))


def _find_order(order_id, user):
    if user.company_id:
        return Order.query.filter_by(id=order_id, company_id=user.company_id).first()
    return Order.query.filter_by(id=order_id, user_id=user.id).first()


def _get_token(company):
    if company and company.token_focusnfe:
        return company.token_focusnfe
    return FOCUS_TOKEN_SANDBOX


def _limpa_cnpj(cnpj):
    if not cnpj:
        return ""
    return "".join(c for c in cnpj if c.isdigit())


def _gera_ref(order):
    """
    Gera o campo 'ref' único obrigatório pela Focus NF-e.
    Formato: svf_{order_id}_{numero_sem_especiais}
    Ex: svf_42_OS20260001
    """
    numero_limpo = "".join(c for c in (order.number or str(order.id)) if c.isalnum())
    return f"svf_{order.id}_{numero_limpo}".lower()[:50]


def _monta_payload_nfe(order, company, client):
    items = json.loads(order.items_json or "[]")
    regime = company.regime_tributario or "1"

    emitente = {
        "cnpj":                  _limpa_cnpj(company.cnpj),
        "nome":                  company.name,
        "logradouro":            company.logradouro or "Rua nao informada",
        "numero":                company.numero or "SN",
        "complemento":           company.complemento or "",
        "bairro":                company.bairro or "Centro",
        "codigo_municipio":      company.codigo_municipio or "4115200",
        "municipio":             company.municipio or "Maringa",
        "uf":                    company.uf or "PR",
        "cep":                   _limpa_cnpj(company.cep or ""),
        "telefone":              _limpa_cnpj(company.telefone or ""),
        "inscricao_estadual":    company.inscricao_estadual or "ISENTO",
        "inscricao_municipal":   company.inscricao_municipal or "",
        "regime_tributario":     regime,
    }

    doc_cliente = _limpa_cnpj(client.document or "")
    destinatario = {
        "nome":               client.name,
        "logradouro":         getattr(client, "logradouro", None) or client.address or "Rua nao informada",
        "numero":             getattr(client, "numero", None) or "SN",
        "complemento":        getattr(client, "complemento", None) or "",
        "bairro":             getattr(client, "bairro", None) or "Centro",
        "codigo_municipio":   getattr(client, "codigo_municipio", None) or "4115200",
        "municipio":          getattr(client, "municipio", None) or "Maringa",
        "uf":                 getattr(client, "uf", None) or "PR",
        "cep":                _limpa_cnpj(getattr(client, "cep", None) or ""),
        "telefone":           _limpa_cnpj(client.phone or ""),
        "email":              client.email or "",
        "inscricao_estadual": getattr(client, "inscricao_estadual", None) or "ISENTO",
    }
    if len(doc_cliente) == 11:
        destinatario["cpf"] = doc_cliente
    elif len(doc_cliente) == 14:
        destinatario["cnpj"] = doc_cliente
    else:
        # sem documento — usa CPF fictício para sandbox
        destinatario["cpf"] = "00000000000"

    itens_nfe = []
    for idx, item in enumerate(items, start=1):
        product_id = item.get("product_id")
        product    = Product.query.get(product_id) if product_id else None
        qty        = float(item.get("qty", 1))
        price      = float(item.get("price", 0))
        total      = round(qty * price, 2)

        ncm        = (product.ncm    if product and product.ncm    else "00000000")
        cfop       = (product.cfop   if product and product.cfop   else "5102")
        origem     = (product.origem if product and product.origem  else "0")
        cst_pis    = (product.cst_pis    if product and product.cst_pis    else "07")
        cst_cofins = (product.cst_cofins if product and product.cst_cofins else "07")

        item_nfe = {
            "numero_item":               idx,
            "codigo_produto":            str(product.sku or product.id) if product else str(idx),
            "descricao":                 item.get("name") or (product.name if product else "Item"),
            "cfop":                      cfop,
            "unidade_comercial":         (product.unit if product and product.unit else "UN"),
            "quantidade_comercial":      qty,
            "valor_unitario_comercial":  price,
            "valor_total_bruto":         total,
            "unidade_tributavel":        (product.unit if product and product.unit else "UN"),
            "quantidade_tributavel":     qty,
            "valor_unitario_tributavel": price,
            "ncm":                       ncm,
            "origem_mercadoria":         origem,
            "entra_total":               "1",
            "icms_modalidade":           "102" if regime in ("1", "4") else "00",
            "pis_modalidade":            cst_pis,
            "cofins_modalidade":         cst_cofins,
        }

        if regime in ("1", "2", "4"):
            csosn = (product.csosn if product and product.csosn else "400")
            item_nfe["icms_csosn"] = csosn
        else:
            cst = (product.cst_icms if product and product.cst_icms else "00")
            item_nfe["icms_cst"]          = cst
            item_nfe["icms_aliquota"]     = 0
            item_nfe["icms_base_calculo"] = total
            item_nfe["icms_valor"]        = 0

        itens_nfe.append(item_nfe)

    payload = {
        "natureza_operacao": "Venda de mercadoria",
        "forma_pagamento":   "0",
        "tipo_documento":    "1",
        "local_destino":     "1",
        "modalidade_frete":  "9",
        "emitente":          emitente,
        "destinatario":      destinatario,
        "items":             itens_nfe,
        "valor_produtos":    round(order.subtotal or order.total, 2),
        "valor_desconto":    round((order.subtotal or order.total) - order.total, 2),
        "valor_total":       round(order.total, 2),
    }

    return payload


def _monta_payload_nfse(order, company, client):
    items    = json.loads(order.items_json or "[]")
    doc_cliente = _limpa_cnpj(client.document or "")

    servicos = []
    for item in items:
        product_id = item.get("product_id")
        product    = Product.query.get(product_id) if product_id else None
        qty        = float(item.get("qty", 1))
        price      = float(item.get("price", 0))
        servicos.append({
            "descricao":                          item.get("name") or (product.name if product else "Servico"),
            "quantidade":                         qty,
            "valor_unitario":                     price,
            "valor_total":                        round(qty * price, 2),
            "codigo_tributacao_municipio":        "0107",
            "aliquota_iss":                       "0.00",
            "iss_retido":                         "false",
        })

    payload = {
        "data_emissao":               order.finished_at or order.created_at,
        "natureza_operacao":          "1",
        "optante_simples_nacional":   "1" if (company.regime_tributario or "1") in ("1","2","4") else "0",
        "prestador": {
            "cnpj":               _limpa_cnpj(company.cnpj),
            "inscricao_municipal": company.inscricao_municipal or "",
            "codigo_municipio":   company.codigo_municipio or "4115200",
        },
        "tomador": {
            "razao_social": client.name,
            "email":        client.email or "",
            "telefone":     _limpa_cnpj(client.phone or ""),
            "endereco": {
                "logradouro":       getattr(client, "logradouro", None) or client.address or "",
                "numero":           getattr(client, "numero", None) or "SN",
                "complemento":      getattr(client, "complemento", None) or "",
                "bairro":           getattr(client, "bairro", None) or "Centro",
                "codigo_municipio": getattr(client, "codigo_municipio", None) or "4115200",
                "uf":               getattr(client, "uf", None) or "PR",
                "cep":              _limpa_cnpj(getattr(client, "cep", None) or ""),
            }
        },
        "servicos":        servicos,
        "valor_servicos":  round(order.total, 2),
        "valor_liquido":   round(order.total, 2),
    }

    if len(doc_cliente) == 11:
        payload["tomador"]["cpf"] = doc_cliente
    elif len(doc_cliente) == 14:
        payload["tomador"]["cnpj"] = doc_cliente

    return payload


# =========================
# POST /api/nfe/emitir/<order_id>
# =========================
@nfe_bp.route("/nfe/emitir/<int:order_id>", methods=["POST"])
@jwt_required()
def emitir_nfe(order_id):
    user  = _get_user(get_jwt_identity())
    order = _find_order(order_id, user)

    if not order:
        return jsonify({"msg": "Pedido não encontrado"}), 404
    if order.status != "done":
        return jsonify({"msg": "Apenas pedidos concluídos podem ter NF-e emitida"}), 400
    if order.nfe_status == "autorizado":
        return jsonify({"msg": "NF-e já autorizada para este pedido", "chave": order.nfe_chave}), 400

    company = user.company
    if not company:
        return jsonify({"msg": "Empresa não encontrada"}), 400
    if not company.cnpj:
        return jsonify({"msg": "CNPJ da empresa não cadastrado. Configure em Configurações → Fiscal."}), 400

    client = order.client
    if not client:
        return jsonify({"msg": "Cliente não encontrado no pedido"}), 400

    token_nfe  = _get_token(company)
    is_servico = order.number.startswith("OS-")

    # ── Gera ref único — OBRIGATÓRIO pela Focus NF-e ──
    ref = _gera_ref(order)

    if is_servico:
        endpoint = f"{FOCUS_URL}/nfse?ref={ref}"
        payload  = _monta_payload_nfse(order, company, client)
    else:
        endpoint = f"{FOCUS_URL}/nfe?ref={ref}"
        payload  = _monta_payload_nfe(order, company, client)

    try:
        resp      = requests.post(endpoint, json=payload, auth=(token_nfe, ""), timeout=30)
        resp_data = resp.json()
    except Exception as e:
        return jsonify({"msg": f"Erro ao conectar com Focus NF-e: {str(e)}"}), 500

    if resp.status_code in (200, 201, 202):
        chave  = resp_data.get("chave_nfe") or resp_data.get("uuid") or ref
        status = resp_data.get("status", "processando")
        numero = resp_data.get("numero_nota_fiscal", "") or resp_data.get("numero", "")

        order.nfe_chave  = chave
        order.nfe_status = status
        order.nfe_numero = str(numero)
        db.session.commit()

        return jsonify({
            "msg":    "NF-e enviada para processamento",
            "status": status,
            "chave":  chave,
            "numero": numero,
            "tipo":   "NFS-e" if is_servico else "NF-e",
            "ref":    ref,
        }), 202

    else:
        erros = resp_data.get("erros") or resp_data.get("mensagem") or str(resp_data)
        return jsonify({
            "msg":   "Erro ao emitir nota fiscal",
            "erros": erros,
            "ref":   ref,
            "raw":   resp_data,
        }), resp.status_code


# =========================
# GET /api/nfe/status/<order_id>
# =========================
@nfe_bp.route("/nfe/status/<int:order_id>", methods=["GET"])
@jwt_required()
def status_nfe(order_id):
    user  = _get_user(get_jwt_identity())
    order = _find_order(order_id, user)

    if not order:
        return jsonify({"msg": "Pedido não encontrado"}), 404
    if not order.nfe_chave:
        return jsonify({"msg": "Nenhuma NF-e emitida para este pedido"}), 404

    company    = user.company
    token_nfe  = _get_token(company)
    is_servico = order.number.startswith("OS-")
    ref        = _gera_ref(order)

    endpoint = f"{FOCUS_URL}/nfse/{ref}" if is_servico else f"{FOCUS_URL}/nfe/{ref}"

    try:
        resp      = requests.get(endpoint, auth=(token_nfe, ""), timeout=15)
        resp_data = resp.json()
    except Exception as e:
        return jsonify({"msg": f"Erro ao consultar Focus NF-e: {str(e)}"}), 500

    novo_status = resp_data.get("status", order.nfe_status)
    if novo_status != order.nfe_status:
        order.nfe_status = novo_status
        db.session.commit()

    return jsonify({
        "order_id":   order_id,
        "nfe_chave":  order.nfe_chave,
        "nfe_status": order.nfe_status,
        "nfe_numero": order.nfe_numero,
        "tipo":       "NFS-e" if is_servico else "NF-e",
        "detalhes":   resp_data,
    }), 200


# =========================
# GET /api/nfe/danfe/<order_id>
# =========================
@nfe_bp.route("/nfe/danfe/<int:order_id>", methods=["GET"])
@jwt_required()
def danfe_nfe(order_id):
    user  = _get_user(get_jwt_identity())
    order = _find_order(order_id, user)

    if not order:
        return jsonify({"msg": "Pedido não encontrado"}), 404
    if not order.nfe_chave:
        return jsonify({"msg": "Nenhuma NF-e emitida para este pedido"}), 404
    if order.nfe_status != "autorizado":
        return jsonify({"msg": f"NF-e ainda não autorizada. Status: {order.nfe_status}"}), 400

    company   = user.company
    token_nfe = _get_token(company)
    ref       = _gera_ref(order)

    danfe_url = f"{FOCUS_URL}/nfe/{ref}/danfe"

    return jsonify({
        "order_id":  order_id,
        "nfe_chave": order.nfe_chave,
        "danfe_url": danfe_url,
    }), 200
