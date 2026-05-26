# app/services/checkin_service.py
"""
CheckinService — lógica de negócio do check-in via QR Code universal.

REGRA DE NEGÓCIO PRINCIPAL:
  O QR Code é universal (mesmo adesivo para todos os clientes).
  A autenticação do local é feita por GPS:
  o colaborador só consegue fazer check-in se estiver
  dentro do raio permitido do endereço cadastrado para o cliente da OS.

FLUXO:
  1. Colaborador seleciona o cliente e a OS no app
  2. Escaneia o QR Code universal
  3. Sistema valida GPS do colaborador vs endereço do cliente
  4. Se aprovado → registra check-in e marca OS como "em andamento"
  5. Ao finalizar → escaneia novamente → check-out + duração calculada
"""

import math
from datetime import datetime, timezone
from app.extensions import db
from app.models import Client, Order, ServiceCheckin, User


# ── Constantes ────────────────────────────────────────────────────────────────

RAIO_MAXIMO_METROS  = 500   # 500m — cobre imprecisão do CEP vs endereço real
RAIO_ADMIN_METROS   = 5000  # admin tem raio maior para testes
QR_CODE_UNIVERSAL   = "sv-checkin-universal"  # token fixo gravado no QR Code


# ── Helpers privados ──────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _diff_minutes(start_str: str, end_str: str) -> int | None:
    """Calcula duração em minutos entre dois timestamps ISO."""
    try:
        fmt   = "%Y-%m-%dT%H:%M:%S"
        start = datetime.strptime(start_str, fmt)
        end   = datetime.strptime(end_str,   fmt)
        return max(0, int((end - start).total_seconds() / 60))
    except Exception:
        return None


def _haversine_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula distância em metros entre dois pontos GPS usando a fórmula Haversine.
    Precisão suficiente para validação de presença em campo.
    """
    R = 6_371_000  # raio da Terra em metros
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi  = math.radians(lat2 - lat1)
    dlam  = math.radians(lon2 - lon1)
    a     = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Serviço principal ─────────────────────────────────────────────────────────

class CheckinService:
    """
    Serviço central de check-in/check-out via QR Code universal.

    Todas as regras de negócio ficam aqui.
    As routes apenas chamam métodos desta classe e retornam JSON.
    """

    # ── Validação do QR Code universal ────────────────────────────────────────

    @staticmethod
    def validar_qr_universal(token: str) -> bool:
        """
        Valida se o QR Code escaneado é o adesivo universal do SV Finance.
        O token é fixo e gravado no QR Code impresso.
        """
        return token.strip() == QR_CODE_UNIVERSAL

    # ── Validação de geolocalização ───────────────────────────────────────────

    @staticmethod
    def validar_geolocalizacao(
        client: Client,
        lat_colaborador: float,
        lon_colaborador: float,
        is_admin: bool = False
    ) -> dict:
        """
        Valida se o colaborador está dentro do raio permitido do cliente.

        Args:
            client:           Model do cliente com coordenadas cadastradas
            lat_colaborador:  Latitude GPS do colaborador no momento do scan
            lon_colaborador:  Longitude GPS do colaborador no momento do scan
            is_admin:         Admins têm raio maior para testes remotos

        Returns:
            dict com 'ok' (bool), 'distancia_metros' (float), 'msg' (str)
        """
        # Se cliente não tem coordenadas cadastradas → permite sem validação GPS
        if not client.latitude or not client.longitude:
            return {
                "ok":               True,
                "distancia_metros": None,
                "msg":              "Cliente sem coordenadas cadastradas — check-in liberado.",
                "sem_coordenadas":  True,
            }

        # Colaborador não enviou GPS
        if lat_colaborador is None or lon_colaborador is None:
            return {
                "ok":               False,
                "distancia_metros": None,
                "msg":              "GPS não disponível. Ative a localização e tente novamente.",
            }

        distancia = _haversine_metros(
            lat_colaborador, lon_colaborador,
            client.latitude, client.longitude
        )

        raio = RAIO_ADMIN_METROS if is_admin else RAIO_MAXIMO_METROS

        if distancia <= raio:
            return {
                "ok":               True,
                "distancia_metros": round(distancia),
                "msg":              f"Localização confirmada ({round(distancia)}m do cliente).",
            }
        else:
            return {
                "ok":               False,
                "distancia_metros": round(distancia),
                "msg":              (
                    f"Você está a {round(distancia)}m do cliente. "
                    f"Aproxime-se (máximo {raio}m) e tente novamente."
                ),
            }

    # ── Check-in (entrada) ────────────────────────────────────────────────────

    @staticmethod
    def registrar_entrada(
        user: User,
        client_id: int,
        order_id: int | None,
        lat: float | None,
        lon: float | None,
        notes: str | None,
        qr_token: str | None,
    ) -> dict:
        """
        Registra a chegada do colaborador no cliente.

        Valida:
          1. QR Code universal
          2. Cliente pertence à empresa do colaborador
          3. OS existe e está aberta
          4. Não há check-in duplicado para a mesma OS
          5. GPS dentro do raio permitido

        Returns:
            dict com dados do check-in criado ou erro
        """
        # 1. Valida QR Code
        if qr_token and not CheckinService.validar_qr_universal(qr_token):
            return {"ok": False, "msg": "QR Code inválido. Use o adesivo oficial SV Finance.", "code": 400}

        # 2. Valida cliente
        client = Client.query.filter_by(id=client_id, company_id=user.company_id).first()
        if not client:
            return {"ok": False, "msg": "Cliente não encontrado.", "code": 404}

        # 3. Valida OS
        order = None
        if order_id:
            order = Order.query.filter_by(id=order_id, company_id=user.company_id).first()
            if not order:
                return {"ok": False, "msg": "O.S não encontrada.", "code": 404}
            if order.status == "done":
                return {"ok": False, "msg": "Esta O.S já foi concluída.", "code": 400}
            if order.client_id != client_id:
                return {"ok": False, "msg": "Esta O.S não pertence a este cliente.", "code": 400}

            # 4. Valida duplicata
            existing = ServiceCheckin.query.filter_by(
                order_id=order_id,
                user_id=user.id,
                type="checkin"
            ).filter(ServiceCheckin.checkout_at == None).first()

            if existing:
                return {
                    "ok":         False,
                    "msg":        "Você já tem um check-in aberto para esta O.S.",
                    "checkin_id": existing.id,
                    "checkin_at": existing.checkin_at,
                    "code":       400,
                }

        # 5. Valida GPS
        geo = CheckinService.validar_geolocalizacao(client, lat, lon, is_admin=user.is_admin)
        if not geo["ok"]:
            return {"ok": False, "msg": geo["msg"], "distancia_metros": geo.get("distancia_metros"), "code": 400}

        # Muda OS para "em andamento"
        if order and order.status == "open":
            order.status = "in_progress"

        now     = _now()
        checkin = ServiceCheckin(
            client_id   =client_id,
            user_id     =user.id,
            company_id  =user.company_id,
            order_id    =order_id,
            executed_at =now,
            checkin_at  =now,
            checkout_at =None,
            duration_min=None,
            type        ="checkin",
            latitude    =lat,
            longitude   =lon,
            notes       =notes.strip() if notes else None,
        )
        db.session.add(checkin)
        db.session.commit()

        return {
            "ok":               True,
            "msg":              "✅ Check-in registrado!",
            "checkin_id":       checkin.id,
            "checkin_at":       checkin.checkin_at,
            "client_name":      client.name,
            "order_id":         order_id,
            "distancia_metros": geo.get("distancia_metros"),
            "geo_msg":          geo["msg"],
            "code":             201,
        }

    # ── Check-out (saída) ─────────────────────────────────────────────────────

    @staticmethod
    def registrar_saida(
        user: User,
        checkin_id: int,
        lat: float | None,
        lon: float | None,
        notes: str | None,
        qr_token: str | None,
    ) -> dict:
        """
        Registra a saída do colaborador e calcula a duração do serviço.

        Valida:
          1. QR Code universal
          2. Check-in existe e pertence ao colaborador
          3. Check-in não foi finalizado ainda
          4. GPS dentro do raio permitido

        Returns:
            dict com dados do check-out ou erro
        """
        # 1. Valida QR Code
        if qr_token and not CheckinService.validar_qr_universal(qr_token):
            return {"ok": False, "msg": "QR Code inválido. Use o adesivo oficial SV Finance.", "code": 400}

        # 2. Busca check-in
        checkin = ServiceCheckin.query.filter_by(
            id=checkin_id,
            user_id=user.id,
            company_id=user.company_id
        ).first()

        if not checkin:
            return {"ok": False, "msg": "Check-in não encontrado.", "code": 404}
        if checkin.checkout_at:
            return {"ok": False, "msg": "Este check-in já foi finalizado.", "code": 400}

        # 3. Valida GPS
        client = Client.query.get(checkin.client_id)
        if client:
            geo = CheckinService.validar_geolocalizacao(client, lat, lon, is_admin=user.is_admin)
            if not geo["ok"]:
                return {"ok": False, "msg": geo["msg"], "distancia_metros": geo.get("distancia_metros"), "code": 400}
        else:
            geo = {"msg": "Cliente não encontrado para validação GPS.", "distancia_metros": None}

        now      = _now()
        duration = _diff_minutes(checkin.checkin_at, now)

        checkin.checkout_at  = now
        checkin.duration_min = duration
        if notes:
            checkin.notes = notes.strip()

        db.session.commit()

        h       = duration // 60 if duration else 0
        m       = duration % 60  if duration else 0
        dur_str = f"{h}h{m:02d}min" if h > 0 else f"{m}min"

        return {
            "ok":               True,
            "msg":              f"✅ Check-out registrado! Duração: {dur_str}",
            "checkin_id":       checkin.id,
            "checkin_at":       checkin.checkin_at,
            "checkout_at":      checkin.checkout_at,
            "duration_min":     duration,
            "duration_str":     dur_str,
            "distancia_metros": geo.get("distancia_metros"),
            "code":             200,
        }

    # ── Checar se há check-in aberto ──────────────────────────────────────────

    @staticmethod
    def buscar_checkin_aberto(user: User) -> dict:
        """
        Retorna o check-in em aberto do colaborador (sem checkout).
        Usado para mostrar o botão "Finalizar" em vez de "Iniciar".
        """
        checkin = ServiceCheckin.query.filter_by(
            user_id=user.id,
            company_id=user.company_id,
            type="checkin"
        ).filter(ServiceCheckin.checkout_at == None).order_by(
            ServiceCheckin.id.desc()
        ).first()

        if not checkin:
            return {"open": False}

        client = Client.query.get(checkin.client_id)
        order  = Order.query.get(checkin.order_id) if checkin.order_id else None

        return {
            "open":         True,
            "checkin_id":   checkin.id,
            "checkin_at":   checkin.checkin_at,
            "client_id":    checkin.client_id,
            "client_name":  client.name if client else "",
            "order_number": order.number if order else "",
            "order_id":     checkin.order_id,
        }

    # ── QR Code universal ─────────────────────────────────────────────────────

    @staticmethod
    def gerar_url_qr_universal() -> str:
        """
        Retorna o token fixo que deve ser gravado no QR Code universal.
        Este token é o mesmo para todos os adesivos — a autenticação
        do local é feita pelo GPS, não pelo QR Code.
        """
        return QR_CODE_UNIVERSAL
