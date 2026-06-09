"""
PinService — geração e validação de PINs de check-in.

Dois tipos de PIN:
1. PIN permanente do cliente (4 dígitos, baseado no código sequencial)
   - Gerado automaticamente ao criar/editar cliente
   - Fica no adesivo QR do cliente
   - Ex: cliente 1 → "0001", cliente 99 → "0099", cliente 1000 → "1000"

2. PIN temporário do admin (6 dígitos, validade 5min, uso único)
   - Gerado pelo admin/encarregado na tela de Autorização de Check-in
   - Para clientes sem GPS cadastrado
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


def gerar_pin_cliente(codigo_seq: int) -> str:
    """
    Gera o PIN permanente de 4+ dígitos baseado no código sequencial do cliente.
    - código 1   → "0001"
    - código 99  → "0099"
    - código 999 → "0999"
    - código 1000 → "1000"
    - código 9999 → "9999"
    - código 10000 → "10000" (cresce naturalmente)
    """
    if codigo_seq < 10000:
        return str(codigo_seq).zfill(4)
    return str(codigo_seq)


class PinService:
    """Serviço central de PINs de check-in."""

    # ── PIN PERMANENTE DO CLIENTE ─────────────────────────────────────────────

    @staticmethod
    def gerar_pin_permanente(client: Client) -> str:
        """
        Gera e salva o PIN permanente do cliente baseado no codigo_seq.
        Chamado automaticamente ao criar/editar cliente.

        Args:
            client: instância do model Client (já com codigo_seq preenchido)

        Returns:
            string com o PIN gerado
        """
        if not client.codigo_seq:
            # Fallback: usa o id do cliente
            pin = gerar_pin_cliente(client.id)
        else:
            pin = gerar_pin_cliente(client.codigo_seq)

        client.pin_cliente = pin
        db.session.commit()
        return pin

    @staticmethod
    def sincronizar_pins_empresa(company_id: int) -> int:
        """
        Sincroniza PINs permanentes de todos os clientes da empresa
        que ainda não têm pin_cliente. Útil para clientes antigos.

        Returns:
            quantidade de clientes atualizados
        """
        clientes = Client.query.filter_by(company_id=company_id).filter(
            Client.pin_cliente == None
        ).all()

        count = 0
        for c in clientes:
            seq = c.codigo_seq or c.id
            c.pin_cliente = gerar_pin_cliente(seq)
            count += 1

        if count:
            db.session.commit()
        return count

    # ── PIN TEMPORÁRIO (ADMIN/ENCARREGADO) ────────────────────────────────────

    @staticmethod
    def gerar(user: User, client_id: int) -> dict:
        """
        Gera um PIN temporário de 6 dígitos para um cliente.

        Args:
            user:       Usuário autenticado (deve ser admin ou encarregado)
            client_id:  ID do cliente que receberá o PIN

        Returns:
            dict com 'ok', 'pin', 'expires_at', 'client_name' e 'code'
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

    # ── VALIDAÇÃO UNIFICADA ───────────────────────────────────────────────────

    @staticmethod
    def validar(user: User, client_id: int, pin: str) -> dict:
        """
        Valida um PIN digitado pelo colaborador.
        Aceita os dois tipos:
        - 4 dígitos (ou mais se cliente > 9999) → PIN permanente do cliente
        - 6 dígitos → PIN temporário gerado pelo admin

        Returns:
            dict com 'ok', 'tipo' ('permanente' | 'temporario'),
            'pin_id' (só temporário, para consumir depois) e 'code'
        """
        pin_str = str(pin).strip()

        if not pin_str:
            return {"ok": False, "msg": "PIN não informado.", "code": 400}

        client = Client.query.filter_by(id=client_id, company_id=user.company_id).first()
        if not client:
            return {"ok": False, "msg": "Cliente não encontrado.", "code": 404}

        # ── Tenta PIN permanente primeiro (4 dígitos) ──
        pin_esperado = client.pin_cliente
        if not pin_esperado and client.codigo_seq:
            pin_esperado = gerar_pin_cliente(client.codigo_seq)
        if not pin_esperado:
            pin_esperado = gerar_pin_cliente(client.id)

        if pin_str == pin_esperado:
            return {
                "ok": True,
                "msg": "PIN permanente válido.",
                "tipo": "permanente",
                "pin_id": None,
                "code": 200,
            }

        # ── Tenta PIN temporário (6 dígitos) ──
        registro = CheckinPin.query.filter_by(
            client_id=client_id,
            company_id=user.company_id,
            pin=pin_str,
            status="ativo",
        ).order_by(CheckinPin.id.desc()).first()

        if not registro:
            return {"ok": False, "msg": "PIN inválido. Verifique e tente novamente.", "code": 400}

        expira = _parse(registro.expires_at)
        if expira and _now_dt() > expira:
            registro.status = "expirado"
            db.session.commit()
            return {"ok": False, "msg": "PIN expirado. Solicite um novo ao encarregado.", "code": 400}

        return {
            "ok": True,
            "msg": "PIN temporário válido.",
            "tipo": "temporario",
            "pin_id": registro.id,
            "code": 200,
        }

    @staticmethod
    def consumir(pin_id: int, user: User) -> None:
        """Marca o PIN temporário como usado. Chamado pelo CheckinService após registrar."""
        if not pin_id:
            return
        registro = CheckinPin.query.get(pin_id)
        if registro and registro.status == "ativo":
            registro.status  = "usado"
            registro.used_by = user.id
            registro.used_at = _fmt(_now_dt())
            db.session.commit()

    @staticmethod
    def listar_ativos(user: User) -> dict:
        """Lista PINs temporários ativos da empresa — painel do admin/encarregado."""
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