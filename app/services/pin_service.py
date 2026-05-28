"""
PinService — geração e validação de PIN temporário de check-in.

Usado quando o cliente NÃO tem GPS cadastrado. O encarregado/admin
gera um PIN de 6 dígitos (validade 5min, uso único). O colaborador
digita o PIN e o check-in é liberado, salvando o GPS dele como
localização oficial do cliente.
"""
import random
from datetime import datetime, timezone, timedelta
from app.extensions import db
from app.models import CheckinPin, Client, User

PIN_VALIDADE_MIN = 5
ROLES_PODE_GERAR = ("admin", "encarregado")


def _now_dt():
    return datetime.now(timezone.utc)

def _fmt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S")

def _parse(s):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        return None


class PinService:
    """Serviço central de PINs temporários de check-in."""

    @staticmethod
    def gerar(user: User, client_id: int) -> dict:
        """
        Gera um PIN temporário para um cliente.

        Args:
            user:       Usuário autenticado (deve ser admin ou encarregado)
            client_id:  ID do cliente que receberá o PIN

        Returns:
            dict com 'ok', 'pin', 'expires_at' e 'code'
        """
        if user.role not in ROLES_PODE_GERAR:
            return {"ok": False, "msg": "Apenas administrador ou encarregado podem gerar PIN.", "code": 403}

        client = Client.query.filter_by(id=client_id, company_id=user.company_id).first()
        if not client:
            return {"ok": False, "msg": "Cliente não encontrado.", "code": 404}

        # Expira PINs ativos antigos do mesmo cliente (só 1 ativo por vez)
        antigos = CheckinPin.query.filter_by(
            client_id=client_id, company_id=user.company_id, status="ativo"
        ).all()
        for p in antigos:
            p.status = "expirado"

        now      = _now_dt()
        pin      = f"{random.randint(0, 999999):06d}"
        registro = CheckinPin(
            pin=pin,
            client_id=client_id,
            company_id=user.company_id,
            created_by=user.id,
            created_at=_fmt(now),
            expires_at=_fmt(now + timedelta(minutes=PIN_VALIDADE_MIN)),
            status="ativo",
        )
        db.session.add(registro)
        db.session.commit()

        return {
            "ok": True,
            "msg": f"PIN gerado. Válido por {PIN_VALIDADE_MIN} minutos.",
            "pin": pin,
            "client_name": client.name,
            "expires_at": registro.expires_at,
            "code": 201,
        }

    @staticmethod
    def validar(user: User, client_id: int, pin: str) -> dict:
        """
        Valida um PIN digitado pelo colaborador.

        NÃO consome o PIN aqui — apenas valida. O consumo (marcar como usado)
        acontece via consumir() após o check-in ser efetivamente registrado.

        Returns:
            dict com 'ok', 'pin_id' (para consumir depois) e 'code'
        """
        registro = CheckinPin.query.filter_by(
            client_id=client_id, company_id=user.company_id,
            pin=str(pin).strip(), status="ativo"
        ).order_by(CheckinPin.id.desc()).first()

        if not registro:
            return {"ok": False, "msg": "PIN inválido.", "code": 400}

        expira = _parse(registro.expires_at)
        if expira and _now_dt() > expira:
            registro.status = "expirado"
            db.session.commit()
            return {"ok": False, "msg": "PIN expirado. Solicite um novo ao encarregado.", "code": 400}

        return {"ok": True, "msg": "PIN válido.", "pin_id": registro.id, "code": 200}

    @staticmethod
    def consumir(pin_id: int, user: User) -> None:
        """Marca o PIN como usado. Chamado pelo CheckinService após registrar o check-in."""
        registro = CheckinPin.query.get(pin_id)
        if registro and registro.status == "ativo":
            registro.status  = "usado"
            registro.used_by = user.id
            registro.used_at = _fmt(_now_dt())
            db.session.commit()

    @staticmethod
    def listar_ativos(user: User) -> dict:
        """Lista PINs ativos da empresa — para o painel do encarregado/admin."""
        if user.role not in ROLES_PODE_GERAR:
            return {"ok": False, "msg": "Sem permissão.", "code": 403}

        pins = CheckinPin.query.filter_by(
            company_id=user.company_id, status="ativo"
        ).order_by(CheckinPin.id.desc()).all()

        now    = _now_dt()
        ativos = []
        for p in pins:
            exp = _parse(p.expires_at)
            if exp and now > exp:
                p.status = "expirado"
            else:
                ativos.append(p.to_dict())
        db.session.commit()
        return {"ok": True, "items": ativos, "code": 200}