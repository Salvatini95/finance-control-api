# app/services/qrcode_service.py
# ─────────────────────────────────────────────────────────────
# SERVICE em POO — toda lógica de QR Code e checkin aqui.
# As routes só chamam os métodos desta classe.
# ─────────────────────────────────────────────────────────────

import qrcode
import qrcode.constants
import io
import base64
import os
from datetime import datetime, timezone


class QRCodeService:
    """
    Gerencia QR Codes mestres por cliente e registros de checkin.

    CONCEITO DO QR CODE MESTRE:
    - Cada cliente tem UM QR Code fixo — não muda nunca.
    - O adesivo fica colado na vitrine do estabelecimento.
    - O colaborador escaneia com o celular → abre a tela de checkin.
    - O checkin registra: quem fez, quando, e opcionalmente onde (GPS).
    - O ADM vê o histórico completo de execuções por cliente.

    MARKETING:
    - O adesivo leva a URL do SV Finance — geração de leads passiva.
    - Quem não tem login vê uma landing page do sistema.
    - Quem tem login vê direto o formulário de checkin.
    """

    APP_URL = os.environ.get("APP_URL", "https://app.svfinance.com.br")

    # ── Geração do QR Code ───────────────────────────────────

    @classmethod
    def generate_master_qr(cls, client_id: int, company_id: int) -> dict:
        """
        Gera o QR Code mestre de um cliente em PNG base64.

        O QR Code aponta para a rota de checkin do SV Finance.
        Sempre o mesmo para aquele cliente — é fixado como adesivo.

        Args:
            client_id:  ID do cliente no banco
            company_id: ID da empresa (multi-tenant)

        Returns:
            dict com 'qr_base64' (PNG) e 'checkin_url' (URL gerada)
        """
        # URL que o colaborador vai abrir ao escanear
        checkin_url = f"{cls.APP_URL}/checkin/{client_id}?c={company_id}"

        qr = qrcode.QRCode(
            version=1,
            # ERROR_CORRECT_H = 30% de redundância — resiste a danos no adesivo
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(checkin_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {
            "qr_base64":   qr_base64,
            "checkin_url": checkin_url,
            "client_id":   client_id,
        }

    # ── Registro de checkin ──────────────────────────────────

    @classmethod
    def register_checkin(
        cls,
        client_id:  int,
        user_id:    int,
        company_id: int,
        lat:        float = None,
        lon:        float = None,
        notes:      str   = None,
    ) -> dict:
        """
        Registra a execução do serviço via scan do QR Code.

        Chamado quando o colaborador confirma o checkin na tela.
        Salva data/hora UTC e coordenadas GPS (se disponíveis).

        Args:
            client_id:  ID do cliente cujo QR foi escaneado
            user_id:    ID do colaborador logado
            company_id: ID da empresa (segurança multi-tenant)
            lat, lon:   Coordenadas GPS do celular (opcional)
            notes:      Observação do colaborador (opcional)

        Returns:
            dict com os dados do checkin criado

        Raises:
            ValueError: se client_id não pertencer à company_id
        """
        from app.models import Client, ServiceCheckin
        from app.extensions import db

        # Garante que o cliente pertence à empresa — segurança multi-tenant
        client = Client.query.filter_by(
            id=client_id,
            company_id=company_id
        ).first()

        if not client:
            raise ValueError(
                f"Cliente {client_id} não encontrado ou não pertence a esta empresa."
            )

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        checkin = ServiceCheckin(
            client_id  = client_id,
            user_id    = user_id,
            company_id = company_id,
            executed_at= now,
            latitude   = lat,
            longitude  = lon,
            notes      = notes,
        )
        db.session.add(checkin)
        db.session.commit()

        return checkin.to_dict()

    # ── Histórico de checkins ────────────────────────────────

    @classmethod
    def get_client_history(
        cls,
        client_id:  int,
        company_id: int,
        limit:      int = 50,
    ) -> list:
        """
        Retorna o histórico de checkins de um cliente.

        Args:
            client_id:  ID do cliente
            company_id: ID da empresa (segurança)
            limit:      Máximo de registros retornados (padrão 50)

        Returns:
            Lista de dicts com os checkins, mais recentes primeiro
        """
        from app.models import ServiceCheckin

        checkins = (
            ServiceCheckin.query
            .filter_by(client_id=client_id, company_id=company_id)
            .order_by(ServiceCheckin.executed_at.desc())
            .limit(limit)
            .all()
        )

        return [c.to_dict() for c in checkins]

    @classmethod
    def get_company_history(
        cls,
        company_id: int,
        date_from:  str = None,
        date_to:    str = None,
        user_id:    int = None,
        limit:      int = 100,
    ) -> list:
        """
        Retorna todos os checkins da empresa com filtros opcionais.
        Usado pelo ADM para ver a operação do dia.

        Args:
            company_id: ID da empresa
            date_from:  Filtro de data início "YYYY-MM-DD" (opcional)
            date_to:    Filtro de data fim "YYYY-MM-DD" (opcional)
            user_id:    Filtrar por colaborador específico (opcional)
            limit:      Máximo de registros (padrão 100)

        Returns:
            Lista de dicts com os checkins
        """
        from app.models import ServiceCheckin

        query = ServiceCheckin.query.filter_by(company_id=company_id)

        if user_id:
            query = query.filter_by(user_id=user_id)

        if date_from:
            query = query.filter(ServiceCheckin.executed_at >= date_from)

        if date_to:
            query = query.filter(ServiceCheckin.executed_at <= f"{date_to}T23:59:59")

        checkins = (
            query
            .order_by(ServiceCheckin.executed_at.desc())
            .limit(limit)
            .all()
        )

        return [c.to_dict() for c in checkins]