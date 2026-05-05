from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Order, Product, User
import json, requests, os

nfe_bp = Blueprint("nfe", __name__)

# URL base do Focus NF-e — sandbox usa o mesmo endpoint com token diferente
FOCUS_URL = "https://homologacao.focusnfe.com.br/v2"

# Token global de fallback (sandbox) — cada empresa pode ter o seu próprio
FOCUS_TOKEN_SANDBOX = os.environ.get("FOCUS_TOKEN_SANDBOX", "66R3bCwxnRBMzyx4QFunliCN8C3GEww1")


def _get_user(user_id):
    return User.query.get(int(user_id))


def _find_order(order_id, user):
    if user.company_id:
        return Order.query.filter_by(id=order_id, company_id=user.company_id).first()
    return Order.query.filter_by(id=order_id, user_id=user.id).first()


def _get_token(company):
    """Usa o token da empresa se tiver, senão usa o token sandbox global."""
    if company and company.token_focusnfe:
        return company.token_focusnfe
    return FOCUS_TOKEN_SANDBOX


def _limpa_cnpj(cnpj):
    """Remove pontuação do CNPJ/CPF."""
    if not cnpj:
        return ""
    return "".join(c for c in cnpj if c.isdigit())


def _monta_payload_nfe(order, company, client):
    """
    Monta o payload da NF-e para o Focus NF-e.
    Documentação: https://focusnfe.com.br/doc/#notas-fiscais-nf-e
    """
    items = json.loads(order.items_json or "[]")
    regime = company.regime_tributario or "1"

    # ── Emitente (sua empresa) ──
    emitente = {
        "cnpj":                  _limpa_cnpj(company.cnpj),
        "nome":                  company.name,
        "logradouro":            company.logradouro or "Rua não informada",
        "numero":                company.numero or "S/N",
        "complemento":           company.complemento or "",
        "bairro":                company.bairro or "Centro",
        "codigo_municipio":      company.codigo_municipio or "",
        "municipio":             company.municipio or "",
        "uf":                    company.uf or "SP",
        "cep":                   _limpa_cnpj(company.cep or ""),
        "telefone":              _limpa_cnpj(company.telefone or ""),
        "inscricao_estadual":    company.inscricao_estadual or "",
        "inscricao_municipal":   company.inscricao_municipal or "",
        "regime_tributario":     regime,
    }

    # ── Destinatário (cliente) ──
    doc_cliente = _limpa_cnpj(client.document or "")
    destinatario = {
        "nome":               client.name,
        "logradouro":         client.logradouro or client.address or "Rua não informada",
        "numero":             client.numero or "S/N",
        "complemento":        client.complemento or "",
        "bairro":             client.bairro or "Centro",
        "codigo_municipio":   client.codigo_municipio or "",
        "municipio":          client.municipio or "",
        "uf":                 client.uf or "SP",
        "cep":                _limpa_cnpj(client.cep or ""),
        "telefone":           _limpa_cnpj(client.phone or ""),
        "email":              client.email or "",
        "inscricao_estadual": client.inscricao_estadual or "ISENTO",
    }
    # CPF ou CNPJ
    if len(doc_cliente) == 11:
        destinatario["cpf"] = doc_cliente
    elif len(doc_cliente) == 14:
        destinatario["cnpj"] = doc_cliente

    # ── Itens ──
    itens_nfe = []
    for idx, item in enumerate(items, start=1):
        product_id = item.get("product_id")
        product = Product.query.get(product_id) if product_id else None

        qty   = float(item.get("qty", 1))
        price = float(item.get("price", 0))
        total = round(qty * price, 2)

        # Campos fiscais — usa do produto se tiver, senão valores padrão
        ncm       = (product.ncm    if product and product.ncm    else "00000000")
        cfop      = (product.cfop   if product and product.cfop   else "5102")
        origem    = (product.origem if product and product.origem  else "0")
        cst_pis   = (product.cst_pis    if product and product.cst_pis    else "07")
        cst_cofins= (product.cst_cofins if product and product.cst_cofins else "07")

        item_nfe = {
            "numero_item":              idx,
            "codigo_produto":           str(product.sku or product.id) if product else str(idx),
            "descricao":                item.get("name") or (product.name if product else "Item"),
            "cfop":                     cfop,
            "unidade_comercial":        (product.unit if product and product.unit else "UN"),
            "quantidade_comercial":     qty,
            "valor_unitario_comercial": price,
            "valor_total_bruto":        total,
            "unidade_tributavel":       (product.unit if product and product.unit else "UN"),
            "quantidade_tributavel":    qty,
            "valor_unitario_tributavel":price,
            "ncm":                      ncm,
            "origem_mercadoria":        origem,
            "entra_total":              "1",
            "icms_modalidade":          "102" if regime in ("1", "4") else "00",
            "pis_modalidade":           cst_pis,
            "cofins_modalidade":        cst_cofins,
        }

        # CSOSN para Simples Nacional
        if regime in ("1", "2", "4"):
            csosn = (product.csosn if product and product.csosn else "400")
            item_nfe["icms_csosn"] = csosn
        else:
            # Regime Normal — CST ICMS
            cst = (product.cst_icms if product and product.cst_icms else "00")
            item_nfe["icms_cst"]              = cst
            item_nfe["icms_aliquota"]         = 0
            item_nfe["icms_base_calculo"]     = total
            item_nfe["icms_valor"]            = 0

        itens_nfe.append(item_nfe)

    # ── Payload completo ──
    payload = {
        "natureza_operacao":    "Venda de mercadoria",
        "forma_pagamento":      "0",  # 0=à vista
        "tipo_documento":       "1",  # 1=saída
        "local_destino":        "1",  # 1=interna
        "modalidade_frete":     "9",  # 9=sem frete
        "emitente":             emitente,
        "destinatario":         destinatario,
        "items":                itens_nfe,
        "valor_produtos":       round(order.subtotal, 2),
        "valor_desconto":       round(order.subtotal - order.total, 2),
        "valor_total":          round(order.total, 2),
    }

    return payload


def _monta_payload_nfse(order, company, client):
    """
    Monta o payload da NFS-e (Nota Fiscal de Serviço Eletrônica).
    Documentação: https://focusnfe.com.br/doc/#nfs-e
    """
    items = json.loads(order.items_json or "[]")

    servicos = []
    for item in items:
        product_id = item.get("product_id")
        product    = Product.query.get(product_id) if product_id else None
        qty        = float(item.get("qty", 1))
        price      = float(item.get("price", 0))
        servicos.append({
            "descricao":        item.get("name") or (product.name if product else "Serviço"),
            "quantidade":       qty,
            "valor_unitario":   price,
            "valor_total":      round(qty * price, 2),
            "codigo_tributacao_municipio": "0107",  # código genérico — ajustar por município
            "aliquota_iss":     "0.00",
            "iss_retido":       "false",
        })

    doc_cliente = _limpa_cnpj(client.document or "")

    payload = {
        "data_emissao":    order.finished_at or order.created_at,
        "natureza_operacao": "1",  # 1=tributação no município
        "optante_simples_nacional": "1" if (company.regime_tributario or "1") in ("1","2","4") else "0",
        "prestador": {
            "cnpj":               _limpa_cnpj(company.cnpj),
            "inscricao_municipal": company.inscricao_municipal or "",
            "codigo_municipio":   company.codigo_municipio or "",
        },
        "tomador": {
            "razao_social": client.name,
            "email":        client.email or "",
            "telefone":     _limpa_cnpj(client.phone or ""),
            "endereco": {
                "logradouro":       client.logradouro or client.address or "",
                "numero":           client.numero or "S/N",
                "complemento":      client.complemento or "",
                "bairro":           client.bairro or "",
                "codigo_municipio": client.codigo_municipio or "",
                "uf":               client.uf or "SP",
                "cep":              _limpa_cnpj(client.cep or ""),
            }
        },
        "servicos": servicos,
        "valor_servicos": round(order.total, 2),
        "valor_liquido":  round(order.total, 2),
    }

    if len(doc_cliente) == 11:
        payload["tomador"]["cpf"] = doc_cliente
    elif len(doc_cliente) == 14:
        payload["tomador"]["cnpj"] = doc_cliente

    return payload


# =========================
# POST /api/nfe/emitir/<order_id>
# Emite NF-e ou NFS-e a partir de um pedido
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
        return jsonify({"msg": "NF-e já foi emitida para este pedido", "chave": order.nfe_chave}), 400

    company = user.company
    if not company:
        return jsonify({"msg": "Empresa não encontrada"}), 400
    if not company.cnpj:
        return jsonify({"msg": "CNPJ da empresa não cadastrado. Configure em Configurações."}), 400

    client = order.client
    if not client:
        return jsonify({"msg": "Cliente não encontrado"}), 400

    token = _get_token(company)

    # Detecta tipo: OS = NFS-e, PED = NF-e
    is_servico = order.number.startswith("OS-")

    if is_servico:
        endpoint = f"{FOCUS_URL}/nfse"
        payload  = _monta_payload_nfse(order, company, client)
    else:
        endpoint = f"{FOCUS_URL}/nfe"
        payload  = _monta_payload_nfe(order, company, client)

    try:
        resp = requests.post(
            endpoint,
            json=payload,
            auth=(token, ""),
            timeout=30,
        )
        resp_data = resp.json()
    except Exception as e:
        return jsonify({"msg": f"Erro ao conectar com Focus NF-e: {str(e)}"}), 500

    # ── Trata retorno ──
    if resp.status_code in (200, 201, 202):
        chave  = resp_data.get("chave_nfe") or resp_data.get("uuid") or ""
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
        }), 202

    else:
        erros = resp_data.get("erros") or resp_data.get("mensagem") or str(resp_data)
        return jsonify({
            "msg":   "Erro ao emitir nota fiscal",
            "erros": erros,
            "raw":   resp_data,
        }), resp.status_code


# =========================
# GET /api/nfe/status/<order_id>
# Consulta o status da NF-e de um pedido
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

    company = user.company
    token   = _get_token(company)
    is_servico = order.number.startswith("OS-")

    endpoint = f"{FOCUS_URL}/nfse/{order.nfe_chave}" if is_servico else f"{FOCUS_URL}/nfe/{order.nfe_chave}"

    try:
        resp      = requests.get(endpoint, auth=(token, ""), timeout=15)
        resp_data = resp.json()
    except Exception as e:
        return jsonify({"msg": f"Erro ao consultar Focus NF-e: {str(e)}"}), 500

    # Atualiza status no banco
    novo_status = resp_data.get("status", order.nfe_status)
    if novo_status != order.nfe_status:
        order.nfe_status = novo_status
        db.session.commit()

    return jsonify({
        "order_id":  order_id,
        "nfe_chave": order.nfe_chave,
        "nfe_status":order.nfe_status,
        "nfe_numero":order.nfe_numero,
        "tipo":      "NFS-e" if is_servico else "NF-e",
        "detalhes":  resp_data,
    }), 200


# =========================
# GET /api/nfe/danfe/<order_id>
# Retorna URL do DANFE (PDF da NF-e)
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
        return jsonify({"msg": f"NF-e ainda não autorizada. Status atual: {order.nfe_status}"}), 400

    company = user.company
    token   = _get_token(company)

    danfe_url = f"{FOCUS_URL}/nfe/{order.nfe_chave}/danfe"

    return jsonify({
        "order_id":  order_id,
        "nfe_chave": order.nfe_chave,
        "danfe_url": danfe_url,
        "token":     token,
        "instrucao": "GET na danfe_url com Authorization Basic token:"
    }), 200