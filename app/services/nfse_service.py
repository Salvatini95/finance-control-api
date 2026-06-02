# app/services/nfse_service.py
# Serviço de emissão de NFS-e via Focus NF-e (intermediadora)
# Documentação: https://focusnfe.com.br/doc/#nfs-e-nacional
#
# Fluxo:
#   1. SV Finance chama NfseService.emitir(order_id, company_id)
#   2. Service monta o payload DPS com dados da Order + Client + Company
#   3. Envia para Focus NF-e (homologação ou produção, via env var)
#   4. Focus assina o XML, faz mTLS com o Portal Nacional e retorna status
#   5. Service salva nfe_numero, nfe_chave e nfe_status na Order
#   6. Retorna {"ok": bool, "msg": str, "code": int, "nfe": dict}

import os
import uuid
import requests
from datetime import datetime
from app.extensions import db
from app.models import Order, Client, Company


# ── Configuração de ambiente ─────────────────────────────────────────────────
FOCUS_ENV = os.environ.get("FOCUS_ENV", "homologacao")  # "homologacao" | "producao"

FOCUS_URLS = {
    "homologacao": "https://homologacao.focusnfe.com.br/v2/nfse",
    "producao":    "https://api.focusnfe.com.br/v2/nfse",
}

# Código IBGE de Maringá-PR
CODIGO_MUNICIPIO_MARINGA = "4115200"

# Regime tributário: 1 = Simples Nacional
REGIME_TRIBUTACAO_SIMPLES = 1

# Códigos de tributação municipal (Maringá)
CODIGO_SERVICO_LIMPEZA     = "1407"   # Limpeza e conservação de vidros
CODIGO_SERVICO_RESTAURACAO = "1405"   # Restauração de vidros

# Natureza da operação: 1 = Tributada no município
NATUREZA_OPERACAO = 1


class NfseService:

    # ── Método principal ─────────────────────────────────────────────────────
    @staticmethod
    def emitir(order_id: int, company_id: int) -> dict:
        """
        Emite NFS-e para uma O.S concluída.
        Retorna {"ok": bool, "msg": str, "code": int, "nfe": dict|None}
        """
        # 1. Carrega dados
        order = Order.query.filter_by(id=order_id, company_id=company_id).first()
        if not order:
            return {"ok": False, "msg": "Ordem de serviço não encontrada.", "code": 404, "nfe": None}

        if order.nfe_status == "autorizada":
            return {"ok": False, "msg": "NFS-e já emitida para esta O.S.", "code": 409, "nfe": None}

        client = Client.query.filter_by(id=order.client_id, company_id=company_id).first()
        if not client:
            return {"ok": False, "msg": "Cliente não encontrado.", "code": 404, "nfe": None}

        company = Company.query.filter_by(id=company_id).first()
        if not company:
            return {"ok": False, "msg": "Empresa não encontrada.", "code": 404, "nfe": None}

        token = company.token_focusnfe
        if not token:
            return {"ok": False, "msg": "Token Focus NF-e não configurado na empresa.", "code": 400, "nfe": None}

        # 2. Gera referência única para idempotência
        ref = f"sv-{order_id}-{uuid.uuid4().hex[:8]}"

        # 3. Monta payload
        payload = NfseService._montar_payload(order, client, company)
        if not payload.get("ok"):
            return {"ok": False, "msg": payload["msg"], "code": 400, "nfe": None}

        # 4. Salva status pendente antes de enviar
        order.nfe_status = "processando"
        order.nfe_ref    = ref
        db.session.commit()

        # 5. Envia para Focus NF-e
        url = f"{FOCUS_URLS[FOCUS_ENV]}?ref={ref}"
        try:
            resp = requests.post(
                url,
                json=payload["data"],
                auth=(token, ""),   # Basic auth: token como usuário, senha vazia
                timeout=30,
            )
        except requests.exceptions.Timeout:
            order.nfe_status = "erro"
            db.session.commit()
            return {"ok": False, "msg": "Timeout ao conectar com Focus NF-e.", "code": 504, "nfe": None}
        except requests.exceptions.ConnectionError:
            order.nfe_status = "erro"
            db.session.commit()
            return {"ok": False, "msg": "Erro de conexão com Focus NF-e.", "code": 503, "nfe": None}

        # 6. Processa resposta
        return NfseService._processar_resposta(resp, order, ref)

    # ── Consulta status (polling) ────────────────────────────────────────────
    @staticmethod
    def consultar(order_id: int, company_id: int) -> dict:
        """
        Consulta o status de uma NFS-e já enviada.
        Útil para checar se saiu de "processando" para "autorizada" ou "erro".
        """
        order = Order.query.filter_by(id=order_id, company_id=company_id).first()
        if not order:
            return {"ok": False, "msg": "O.S não encontrada.", "code": 404, "nfe": None}

        if not order.nfe_ref:
            return {"ok": False, "msg": "Nenhuma NFS-e emitida para esta O.S.", "code": 404, "nfe": None}

        company = Company.query.filter_by(id=company_id).first()
        token   = company.token_focusnfe if company else None
        if not token:
            return {"ok": False, "msg": "Token Focus NF-e não configurado.", "code": 400, "nfe": None}

        url = f"{FOCUS_URLS[FOCUS_ENV]}/{order.nfe_ref}"
        try:
            resp = requests.get(url, auth=(token, ""), timeout=15)
        except Exception as e:
            return {"ok": False, "msg": f"Erro ao consultar: {str(e)}", "code": 503, "nfe": None}

        return NfseService._processar_resposta(resp, order, order.nfe_ref)

    # ── Monta payload DPS ────────────────────────────────────────────────────
    @staticmethod
    def _montar_payload(order, client, company) -> dict:
        """
        Monta o payload DPS (Documento de Prestação de Serviço) para o Focus NF-e.
        Retorna {"ok": bool, "msg": str, "data": dict}
        """
        # Validações básicas
        valor = float(order.total or 0)
        if valor <= 0:
            return {"ok": False, "msg": "Valor da O.S deve ser maior que zero."}

        # Determina código de serviço pelo nicho/produto
        # Por padrão usa limpeza (1407). Se quiser por produto, expanda aqui.
        codigo_servico = CODIGO_SERVICO_LIMPEZA

        # Discriminação do serviço (descrição que vai na nota)
        itens = order.items or []
        if itens:
            discriminacao = "; ".join(
                f"{i.get('name', 'Serviço')} (qtd: {i.get('qty', 1)})"
                for i in itens
            )
        else:
            discriminacao = f"Serviço de limpeza e conservação de vidros — O.S {order.number}"

        discriminacao = discriminacao[:2000]  # limite do campo

        # Data de emissão
        data_emissao = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S-03:00")

        # Tomador (cliente)
        tomador = NfseService._montar_tomador(client)

        payload = {
            "data_emissao":       data_emissao,
            "natureza_operacao":  NATUREZA_OPERACAO,
            "prestador": {
                "cnpj":                    "11245238000101",   # sem pontuação
                "codigo_municipio":        CODIGO_MUNICIPIO_MARINGA,
                "regime_tributacao":       REGIME_TRIBUTACAO_SIMPLES,
            },
            "tomador": tomador,
            "servico": {
                "codigo_tributacao_municipio": codigo_servico,
                "discriminacao":               discriminacao,
                "municipio_prestacao_servico": CODIGO_MUNICIPIO_MARINGA,
                "valor_servicos":              round(valor, 2),
                "valor_deducoes":              0,
                "valor_pis":                   0,
                "valor_cofins":                0,
                "valor_inss":                  0,
                "valor_ir":                    0,
                "valor_csll":                  0,
                "iss_retido":                  False,
                "valor_iss":                   0,      # Simples: ISS já incluso no DAS
                "base_calculo":                round(valor, 2),
                "aliquota":                    0,      # Simples Nacional não destaca alíquota
                "valor_liquido_nfse":          round(valor, 2),
            },
        }

        return {"ok": True, "data": payload}

    # ── Monta dados do tomador (cliente) ─────────────────────────────────────
    @staticmethod
    def _montar_tomador(client) -> dict:
        """
        Monta o bloco do tomador. CPF/CNPJ é opcional no Portal Nacional
        quando o tomador é pessoa física sem documento cadastrado.
        """
        tomador = {
            "razao_social": (client.name or "Consumidor Final")[:150],
        }

        # CPF ou CNPJ (remove pontuação)
        doc = (client.document or "").replace(".", "").replace("-", "").replace("/", "").strip()
        if len(doc) == 11:
            tomador["cpf"] = doc
        elif len(doc) == 14:
            tomador["cnpj"] = doc
        # sem documento: Focus aceita sem CPF/CNPJ para PF

        # Email (opcional mas recomendado — o Portal Nacional envia a nota pro tomador)
        if client.email:
            tomador["email"] = client.email

        # Endereço (opcional)
        if client.logradouro and client.municipio:
            tomador["endereco"] = {
                "logradouro":  client.logradouro or "",
                "numero":      client.numero     or "S/N",
                "bairro":      client.bairro     or "",
                "codigo_municipio": CODIGO_MUNICIPIO_MARINGA,
                "uf":          client.uf         or "PR",
                "cep":         (client.cep or "").replace("-", ""),
            }

        return tomador

    # ── Processa resposta do Focus ────────────────────────────────────────────
    @staticmethod
    def _processar_resposta(resp, order, ref) -> dict:
        """
        Interpreta a resposta HTTP do Focus NF-e e atualiza a Order.
        """
        try:
            data = resp.json()
        except Exception:
            data = {}

        status_focus = data.get("status", "")
        numero       = data.get("numero_nfse") or data.get("numero")
        chave        = data.get("chave_nfe")   or data.get("chave")

        # Mapa de status Focus → status interno
        if status_focus in ("autorizado", "autorizada"):
            order.nfe_status = "autorizada"
            order.nfe_numero = str(numero) if numero else order.nfe_numero
            order.nfe_chave  = str(chave)  if chave  else order.nfe_chave
            db.session.commit()
            return {
                "ok":   True,
                "msg":  f"NFS-e emitida com sucesso! Número: {order.nfe_numero}",
                "code": 200,
                "nfe":  {
                    "numero": order.nfe_numero,
                    "chave":  order.nfe_chave,
                    "status": "autorizada",
                    "ref":    ref,
                    "url_danfse": data.get("url_danfse") or data.get("caminho_danfse"),
                },
            }

        elif status_focus in ("processando", "aguardando_autorizacao"):
            order.nfe_status = "processando"
            db.session.commit()
            return {
                "ok":   True,
                "msg":  "NFS-e enviada e aguardando autorização do Portal Nacional.",
                "code": 202,
                "nfe":  {"status": "processando", "ref": ref},
            }

        elif status_focus in ("erro", "rejeitado", "cancelado"):
            erros = data.get("erros") or data.get("mensagem_sefaz") or str(data)
            order.nfe_status = "erro"
            db.session.commit()
            return {
                "ok":   False,
                "msg":  f"Focus NF-e retornou erro: {erros}",
                "code": 422,
                "nfe":  {"status": "erro", "ref": ref, "detalhes": erros},
            }

        else:
            # Status desconhecido ou resposta inesperada
            order.nfe_status = "processando"
            db.session.commit()
            return {
                "ok":   True,
                "msg":  f"NFS-e enviada. Status atual: {status_focus or 'aguardando'}",
                "code": 202,
                "nfe":  {"status": status_focus, "ref": ref, "raw": data},
            }