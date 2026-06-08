"""
AsaasService — integração com a API do Asaas para cobranças SaaS.

Responsabilidades:
- Criar/buscar cliente no Asaas (por company_id)
- Criar assinatura mensal ou anual com cartão ou Pix
- Processar eventos de webhook (pagamento confirmado, vencido, cancelado)
- Atualizar plan/status na Company e na tabela Subscription
- Ativar trial de 7 dias sem cartão

Variáveis de ambiente necessárias:
  ASAAS_API_KEY  → chave da conta (sandbox: $aas_xxx... / produção: $aas_xxx...)
  ASAAS_ENV      → "sandbox" ou "production"
"""
import os
import requests
from datetime import datetime, timedelta
from app.extensions import db
from app.models import Company, Subscription


# ── Preços por plano/intervalo (Fase 1 — Fundador) ───────────────────────────
PLANOS = {
    "pro": {
        "monthly": 49.00,
        "yearly":  468.00,   # R$39/mês × 12
    },
    "business": {
        "monthly": 99.00,
        "yearly":  948.00,   # R$79/mês × 12
    },
}

TRIAL_DIAS = 7


class AsaasService:
    """
    Serviço central de cobrança SaaS via Asaas.

    Todas as chamadas HTTP ao Asaas ficam aqui.
    As routes apenas chamam métodos desta classe e retornam JSON.
    """

    # ── Configuração interna ──────────────────────────────────────────────────

    @staticmethod
    def _base_url() -> str:
        env = os.environ.get("ASAAS_ENV", "sandbox")
        if env == "production":
            return "https://api.asaas.com/v3"
        return "https://sandbox.asaas.com/api/v3"

    @staticmethod
    def _headers() -> dict:
        return {
            "Content-Type": "application/json",
            "access_token": os.environ.get("ASAAS_API_KEY", ""),
        }

    @classmethod
    def _post(cls, endpoint: str, payload: dict) -> dict:
        """Executa POST na API do Asaas e retorna dict da resposta."""
        url = f"{cls._base_url()}{endpoint}"
        resp = requests.post(url, json=payload, headers=cls._headers(), timeout=15)
        return resp.json()

    @classmethod
    def _get(cls, endpoint: str) -> dict:
        """Executa GET na API do Asaas e retorna dict da resposta."""
        url = f"{cls._base_url()}{endpoint}"
        resp = requests.get(url, headers=cls._headers(), timeout=15)
        return resp.json()

    # ── Clientes Asaas ────────────────────────────────────────────────────────

    @classmethod
    def criar_ou_buscar_cliente(cls, company: Company, dados_titular: dict) -> dict:
        """
        Cria um cliente no Asaas ou retorna o existente (por externalReference).

        Args:
            company:       Model Company do assinante
            dados_titular: {'name', 'cpfCnpj', 'email', 'phone', 'postalCode'}

        Returns:
            dict com 'ok', 'asaas_customer_id', 'code'
        """
        # Busca por externalReference para evitar duplicatas
        busca = cls._get(f"/customers?externalReference=company_{company.id}")
        dados_lista = busca.get("data", [])

        if dados_lista:
            customer_id = dados_lista[0]["id"]
        else:
            payload = {
                "name":              dados_titular.get("name", company.name),
                "cpfCnpj":           dados_titular.get("cpfCnpj", ""),
                "email":             dados_titular.get("email", ""),
                "mobilePhone":       dados_titular.get("phone", ""),
                "postalCode":        dados_titular.get("postalCode", ""),
                "externalReference": f"company_{company.id}",
                "notificationDisabled": False,
            }
            resp = cls._post("/customers", payload)

            if resp.get("errors") or not resp.get("id"):
                erros = resp.get("errors", [{"description": "Erro desconhecido"}])
                return {"ok": False, "msg": erros[0].get("description", "Erro Asaas"), "code": 400}

            customer_id = resp["id"]

        # Persiste asaas_customer_id na Company
        company.asaas_customer_id = customer_id
        db.session.commit()

        return {"ok": True, "asaas_customer_id": customer_id, "code": 200}

    # ── Trial ─────────────────────────────────────────────────────────────────

    @classmethod
    def iniciar_trial(cls, company: Company) -> dict:
        """
        Inicia período de trial de 7 dias sem cartão.

        Cria registro local na tabela subscriptions com status='trial'.
        Não chama o Asaas ainda — só na conversão.

        Args:
            company: Model Company

        Returns:
            dict com 'ok', 'trial_ends_at', 'code'
        """
        # Verifica se já tem trial ou assinatura ativa
        sub_existente = Subscription.query.filter_by(company_id=company.id).first()
        if sub_existente:
            return {"ok": False, "msg": "Empresa já possui assinatura registrada.", "code": 409}

        trial_ends = (datetime.utcnow() + timedelta(days=TRIAL_DIAS)).strftime("%Y-%m-%d")

        sub = Subscription(
            company_id    = company.id,
            plan          = "pro",
            interval      = "monthly",
            status        = "trial",
            valor         = 0.0,
            trial_ends_at = trial_ends,
            founder       = True,
            billing_type  = "PIX",
            created_at    = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        )
        db.session.add(sub)

        company.plan          = "pro"
        company.trial_ends_at = trial_ends
        db.session.commit()

        return {"ok": True, "trial_ends_at": trial_ends, "code": 201}

    # ── Assinatura ────────────────────────────────────────────────────────────

    @classmethod
    def criar_assinatura(cls, company: Company, dados: dict) -> dict:
        """
        Cria assinatura recorrente no Asaas e registra localmente.

        Args:
            company: Model Company
            dados: {
                'plan':         'pro' | 'business',
                'interval':     'monthly' | 'yearly',
                'billing_type': 'PIX' | 'CREDIT_CARD',
                'titular': {'name', 'cpfCnpj', 'email', 'phone', 'postalCode'},
                'credit_card': {...}  ← opcional, só se billing_type=CREDIT_CARD
            }

        Returns:
            dict com 'ok', 'msg', 'subscription', 'code'
        """
        plano    = dados.get("plan", "pro")
        interval = dados.get("interval", "monthly")

        if plano not in PLANOS:
            return {"ok": False, "msg": "Plano inválido. Use 'pro' ou 'business'.", "code": 400}
        if interval not in ("monthly", "yearly"):
            return {"ok": False, "msg": "Intervalo inválido. Use 'monthly' ou 'yearly'.", "code": 400}

        valor = PLANOS[plano][interval]

        # 1. Garante cliente no Asaas
        res_cliente = cls.criar_ou_buscar_cliente(company, dados.get("titular", {}))
        if not res_cliente["ok"]:
            return res_cliente

        customer_id = res_cliente["asaas_customer_id"]

        # 2. Calcula data do primeiro vencimento (agora — trial já acabou)
        next_due = datetime.utcnow().strftime("%Y-%m-%d")

        # 3. Monta payload da assinatura
        billing_type = dados.get("billing_type", "PIX")
        cycle        = "MONTHLY" if interval == "monthly" else "YEARLY"

        payload = {
            "customer":         customer_id,
            "billingType":      billing_type,
            "value":            valor,
            "nextDueDate":      next_due,
            "cycle":            cycle,
            "description":      f"SV Finance — Plano {plano.capitalize()} ({interval})",
            "externalReference": f"company_{company.id}_plan_{plano}",
        }

        # Cartão de crédito — dados do titular obrigatórios
        if billing_type == "CREDIT_CARD":
            cc = dados.get("credit_card")
            if not cc:
                return {"ok": False, "msg": "Dados do cartão são obrigatórios para pagamento em cartão.", "code": 400}

            titular = dados.get("titular", {})
            payload["creditCard"] = {
                "holderName":  cc.get("holderName"),
                "number":      cc.get("number"),
                "expiryMonth": cc.get("expiryMonth"),
                "expiryYear":  cc.get("expiryYear"),
                "ccv":         cc.get("ccv"),
            }
            payload["creditCardHolderInfo"] = {
                "name":          titular.get("name"),
                "email":         titular.get("email"),
                "cpfCnpj":       titular.get("cpfCnpj"),
                "postalCode":    titular.get("postalCode"),
                "addressNumber": titular.get("addressNumber", "S/N"),
                "phone":         titular.get("phone", ""),
            }

        # 4. Cria assinatura no Asaas
        resp = cls._post("/subscriptions", payload)

        if resp.get("errors") or not resp.get("id"):
            erros = resp.get("errors", [{"description": "Erro desconhecido no Asaas"}])
            return {"ok": False, "msg": erros[0].get("description", "Erro Asaas"), "code": 400}

        asaas_sub_id = resp["id"]

        # 5. Atualiza ou cria registro local
        sub = Subscription.query.filter_by(company_id=company.id).first()
        agora = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        if sub:
            sub.asaas_subscription_id = asaas_sub_id
            sub.asaas_customer_id     = customer_id
            sub.plan                  = plano
            sub.interval              = interval
            sub.status                = "active"
            sub.valor                 = valor
            sub.billing_type          = billing_type
            sub.next_due_date         = next_due
            sub.last_event            = "SUBSCRIPTION_CREATED"
            sub.last_event_at         = agora
        else:
            sub = Subscription(
                company_id             = company.id,
                asaas_subscription_id  = asaas_sub_id,
                asaas_customer_id      = customer_id,
                plan                   = plano,
                interval               = interval,
                status                 = "active",
                valor                  = valor,
                billing_type           = billing_type,
                next_due_date          = next_due,
                founder                = True,
                last_event             = "SUBSCRIPTION_CREATED",
                last_event_at          = agora,
                created_at             = agora,
            )
            db.session.add(sub)

        # 6. Atualiza Company
        company.plan          = plano
        company.plan_interval = interval
        company.plan_locked_at = agora   # trava preço de fundador

        db.session.commit()

        return {
            "ok":           True,
            "msg":          f"Plano {plano.capitalize()} ativado com sucesso!",
            "subscription": sub.to_dict(),
            "code":         201,
        }

    # ── Consulta de status ────────────────────────────────────────────────────

    @classmethod
    def status_assinatura(cls, company: Company) -> dict:
        """
        Retorna o status atual da assinatura da empresa.

        Args:
            company: Model Company

        Returns:
            dict com 'ok', 'subscription', 'code'
        """
        sub = Subscription.query.filter_by(company_id=company.id).order_by(
            Subscription.id.desc()
        ).first()

        if not sub:
            return {
                "ok": True,
                "subscription": {
                    "plan":   "free",
                    "status": "sem_assinatura",
                },
                "code": 200,
            }

        return {"ok": True, "subscription": sub.to_dict(), "code": 200}

    # ── Webhook ───────────────────────────────────────────────────────────────

    @classmethod
    def processar_webhook(cls, evento: str, payload: dict) -> dict:
        """
        Processa evento de webhook enviado pelo Asaas.

        Eventos tratados:
          PAYMENT_CONFIRMED / PAYMENT_RECEIVED → ativa assinatura
          PAYMENT_OVERDUE                       → marca como inadimplente
          PAYMENT_DELETED / SUBSCRIPTION_DELETED → cancela
          PAYMENT_REFUNDED                       → cancela

        Args:
            evento:  string do evento (ex: "PAYMENT_CONFIRMED")
            payload: dict completo do webhook do Asaas

        Returns:
            dict com 'ok', 'msg', 'code'
        """
        # Extrai external_reference para localizar a company
        external_ref = (
            payload.get("subscription", {}).get("externalReference")
            or payload.get("payment", {}).get("externalReference")
            or ""
        )

        company_id = cls._extrair_company_id(external_ref)
        if not company_id:
            # Webhook de outro contexto — ignora silenciosamente
            return {"ok": True, "msg": "Evento ignorado (sem externalReference válido).", "code": 200}

        company = Company.query.get(company_id)
        if not company:
            return {"ok": False, "msg": "Empresa não encontrada.", "code": 404}

        sub = Subscription.query.filter_by(company_id=company_id).order_by(
            Subscription.id.desc()
        ).first()

        agora = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        if evento in ("PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"):
            if sub:
                sub.status        = "active"
                sub.last_event    = evento
                sub.last_event_at = agora
            company.plan = sub.plan if sub else "pro"

        elif evento == "PAYMENT_OVERDUE":
            if sub:
                sub.status        = "overdue"
                sub.last_event    = evento
                sub.last_event_at = agora
            # Não rebaixa o plan — só marca overdue para o guard de rota tratar

        elif evento in ("PAYMENT_DELETED", "PAYMENT_REFUNDED", "SUBSCRIPTION_DELETED"):
            if sub:
                sub.status        = "canceled"
                sub.last_event    = evento
                sub.last_event_at = agora
            company.plan = "free"

        db.session.commit()

        return {"ok": True, "msg": f"Evento {evento} processado.", "code": 200}

    # ── Cancelamento ──────────────────────────────────────────────────────────

    @classmethod
    def cancelar_assinatura(cls, company: Company) -> dict:
        """
        Cancela assinatura ativa no Asaas e atualiza status local.

        Args:
            company: Model Company

        Returns:
            dict com 'ok', 'msg', 'code'
        """
        sub = Subscription.query.filter_by(company_id=company.id).order_by(
            Subscription.id.desc()
        ).first()

        if not sub or not sub.asaas_subscription_id:
            return {"ok": False, "msg": "Nenhuma assinatura ativa encontrada.", "code": 404}

        resp = cls._post(f"/subscriptions/{sub.asaas_subscription_id}/cancel", {})

        if resp.get("errors"):
            erros = resp.get("errors", [{"description": "Erro desconhecido"}])
            return {"ok": False, "msg": erros[0].get("description", "Erro Asaas"), "code": 400}

        agora         = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        sub.status        = "canceled"
        sub.last_event    = "SUBSCRIPTION_CANCELED"
        sub.last_event_at = agora
        company.plan      = "free"

        db.session.commit()

        return {"ok": True, "msg": "Assinatura cancelada com sucesso.", "code": 200}

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extrair_company_id(external_ref: str) -> int | None:
        """
        Extrai company_id de strings no formato 'company_42_plan_pro'.

        Args:
            external_ref: string externalReference do Asaas

        Returns:
            int company_id ou None se não encontrar
        """
        if not external_ref or not external_ref.startswith("company_"):
            return None
        try:
            partes = external_ref.split("_")
            return int(partes[1])
        except (IndexError, ValueError):
            return None