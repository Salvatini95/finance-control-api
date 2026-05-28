# app/services/checkin_service.py
import math
import uuid
from datetime import datetime, timezone, date
from app.extensions import db
from app.models import Client, Order, ServiceCheckin, User
from app.services.pin_service import PinService

RAIO_MAXIMO_METROS = 300
RAIO_ADMIN_METROS  = 10000
QR_CODE_UNIVERSAL  = "sv-checkin-universal"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def _diff_minutes(start_str, end_str):
    try:
        fmt   = "%Y-%m-%dT%H:%M:%S"
        start = datetime.strptime(start_str, fmt)
        end   = datetime.strptime(end_str,   fmt)
        return max(0, int((end - start).total_seconds() / 60))
    except Exception:
        return None

def _haversine_metros(lat1, lon1, lat2, lon2):
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


class CheckinService:

    @staticmethod
    def validar_qr_universal(token):
        return str(token).strip() == QR_CODE_UNIVERSAL

    @staticmethod
    def validar_geolocalizacao(client, lat, lon, is_admin=False):
        """
        Valida presença por GPS.

        - Cliente SEM coordenadas → BLOQUEIA (precisa de PIN do encarregado).
        - Colaborador sem GPS      → BLOQUEIA (não dá pra registrar local).
        - Dentro do raio           → ok, msg genérica.
        - Fora do raio             → bloqueia, msg genérica (sem distância/raio).

        distancia_metros vai no dict para o ADM, nunca na msg do colaborador.
        """
        if not client.latitude or not client.longitude:
            return {
                "ok": False,
                "distancia_metros": None,
                "msg": "Este cliente não tem localização cadastrada. Solicite um PIN ao seu encarregado.",
                "sem_coordenadas": True,
            }
        if lat is None or lon is None:
            return {
                "ok": False,
                "distancia_metros": None,
                "msg": "GPS não disponível. Ative a localização e tente novamente.",
                "sem_gps": True,
            }

        distancia = _haversine_metros(lat, lon, client.latitude, client.longitude)
        raio      = RAIO_ADMIN_METROS if is_admin else RAIO_MAXIMO_METROS

        if distancia <= raio:
            return {"ok": True, "distancia_metros": round(distancia), "msg": "📍 Localização confirmada."}

        return {
            "ok": False,
            "distancia_metros": round(distancia),
            "msg": "❌ Você não está no local do cliente. Aproxime-se e tente novamente.",
        }

    @staticmethod
    def registrar_entrada(user, client_id, order_id, lat, lon, notes, qr_token,
                          pin=None, local_id=None, synced_offline=False):
        """
        Registra entrada (check-in).

        Se o cliente não tem GPS e um PIN válido for fornecido:
          → libera o check-in
          → salva o GPS do colaborador como localização oficial do cliente
          → consome o PIN

        local_id: UUID gerado no celular (idempotência offline).
        """
        if qr_token and not CheckinService.validar_qr_universal(qr_token):
            return {"ok": False, "msg": "QR Code inválido.", "code": 400}

        # Idempotência: se já existe esse local_id, retorna sucesso sem duplicar
        if local_id:
            dup = ServiceCheckin.query.filter_by(local_id=local_id, company_id=user.company_id).first()
            if dup:
                return {"ok": True, "msg": "Check-in já registrado.", "checkin_id": dup.id,
                        "checkin_at": dup.checkin_at, "client_name": "", "order_id": dup.order_id,
                        "duplicate": True, "code": 200}

        client = Client.query.filter_by(id=client_id, company_id=user.company_id).first()
        if not client:
            return {"ok": False, "msg": "Cliente não encontrado.", "code": 404}

        order = None
        if order_id:
            order = Order.query.filter_by(id=order_id, company_id=user.company_id).first()
            if not order:
                return {"ok": False, "msg": "O.S não encontrada.", "code": 404}
            if order.status == "done":
                return {"ok": False, "msg": "Esta O.S já foi concluída.", "code": 400}
            if order.client_id != client_id:
                return {"ok": False, "msg": "Esta O.S não pertence a este cliente.", "code": 400}

            existing = ServiceCheckin.query.filter_by(
                order_id=order_id, user_id=user.id, type="checkin"
            ).filter(ServiceCheckin.checkout_at == None).first()
            if existing:
                return {"ok": False, "msg": "Você já tem um check-in aberto para esta O.S.",
                        "checkin_id": existing.id, "checkin_at": existing.checkin_at, "code": 400}

        # ── Fluxo PIN: cliente sem GPS + PIN fornecido ──────────────────────────
        pin_id = None
        if pin and (not client.latitude or not client.longitude):
            valida = PinService.validar(user, client_id, pin)
            if not valida["ok"]:
                return {"ok": False, "msg": valida["msg"], "code": valida["code"]}
            pin_id = valida["pin_id"]
            # Salva o GPS do colaborador como localização oficial do cliente
            if lat is not None and lon is not None:
                client.latitude  = lat
                client.longitude = lon
        else:
            # Validação normal de GPS
            geo = CheckinService.validar_geolocalizacao(client, lat, lon, is_admin=user.is_admin)
            if not geo["ok"]:
                return {"ok": False, "msg": geo["msg"],
                        "distancia_metros": geo.get("distancia_metros"),
                        "sem_coordenadas": geo.get("sem_coordenadas", False),
                        "code": 400}

        if order and order.status == "open":
            order.status = "in_progress"

        now = _now()
        checkin = ServiceCheckin(
            client_id=client_id, user_id=user.id, company_id=user.company_id,
            order_id=order_id, executed_at=now, checkin_at=now,
            checkout_at=None, duration_min=None, type="checkin",
            latitude=lat, longitude=lon,
            notes=notes.strip() if notes else None,
            local_id=local_id or str(uuid.uuid4()),
            synced_offline=bool(synced_offline),
        )
        db.session.add(checkin)
        db.session.commit()

        # Consome o PIN só após o check-in existir
        if pin_id:
            PinService.consumir(pin_id, user)

        return {
            "ok": True, "msg": "✅ Check-in registrado!",
            "checkin_id": checkin.id, "checkin_at": checkin.checkin_at,
            "client_name": client.name, "order_id": order_id,
            "local_id": checkin.local_id,
            "geo_msg": "📍 Localização confirmada.", "code": 201,
        }

    @staticmethod
    def registrar_saida(user, checkin_id, lat, lon, notes, qr_token,
                        pin=None, local_id=None, synced_offline=False):
        """Registra saída (check-out). Mesma lógica de PIN/idempotência da entrada."""
        if qr_token and not CheckinService.validar_qr_universal(qr_token):
            return {"ok": False, "msg": "QR Code inválido.", "code": 400}

        checkin = ServiceCheckin.query.filter_by(
            id=checkin_id, user_id=user.id, company_id=user.company_id
        ).first()
        if not checkin:
            return {"ok": False, "msg": "Check-in não encontrado.", "code": 404}
        if checkin.checkout_at:
            return {"ok": False, "msg": "Este check-in já foi finalizado.", "code": 400}

        client = Client.query.get(checkin.client_id)
        pin_id = None
        if client:
            if pin and (not client.latitude or not client.longitude):
                valida = PinService.validar(user, client.id, pin)
                if not valida["ok"]:
                    return {"ok": False, "msg": valida["msg"], "code": valida["code"]}
                pin_id = valida["pin_id"]
                if lat is not None and lon is not None:
                    client.latitude  = lat
                    client.longitude = lon
            else:
                geo = CheckinService.validar_geolocalizacao(client, lat, lon, is_admin=user.is_admin)
                if not geo["ok"]:
                    return {"ok": False, "msg": geo["msg"],
                            "distancia_metros": geo.get("distancia_metros"),
                            "sem_coordenadas": geo.get("sem_coordenadas", False), "code": 400}

        now      = _now()
        duration = _diff_minutes(checkin.checkin_at, now)
        checkin.checkout_at  = now
        checkin.duration_min = duration
        if notes:
            checkin.notes = notes.strip()

        if checkin.order_id:
            order = Order.query.get(checkin.order_id)
            if order and order.status == "in_progress":
                order.status      = "done"
                order.finished_at = str(date.today())

        db.session.commit()
        if pin_id:
            PinService.consumir(pin_id, user)

        h       = duration // 60 if duration else 0
        m       = duration % 60  if duration else 0
        dur_str = f"{h}h{m:02d}min" if h > 0 else f"{m}min"

        return {
            "ok": True, "msg": f"✅ Serviço concluído! Duração: {dur_str}",
            "checkin_id": checkin.id, "checkin_at": checkin.checkin_at,
            "checkout_at": checkin.checkout_at, "duration_min": duration,
            "duration_str": dur_str, "order_status": "done", "code": 200,
        }

    @staticmethod
    def sincronizar_lote(user, eventos: list) -> dict:
        """
        Sincroniza uma fila de check-ins feitos offline.

        Cada evento: {
          "local_id": "uuid", "kind": "start"|"finish",
          "client_id": int, "order_id": int|null, "checkin_id": int|null,
          "lat": float, "lon": float, "notes": str, "pin": str|null
        }

        Idempotência por local_id: eventos já processados são ignorados.

        Returns:
            dict com 'ok', 'results' (lista de {local_id, ok, msg}) e 'code'
        """
        results = []
        for ev in eventos:
            lid = ev.get("local_id")
            try:
                if ev.get("kind") == "start":
                    r = CheckinService.registrar_entrada(
                        user=user, client_id=ev.get("client_id"), order_id=ev.get("order_id"),
                        lat=ev.get("lat"), lon=ev.get("lon"), notes=ev.get("notes"),
                        qr_token=QR_CODE_UNIVERSAL, pin=ev.get("pin"),
                        local_id=lid, synced_offline=True,
                    )
                else:  # finish
                    r = CheckinService.registrar_saida(
                        user=user, checkin_id=ev.get("checkin_id"),
                        lat=ev.get("lat"), lon=ev.get("lon"), notes=ev.get("notes"),
                        qr_token=QR_CODE_UNIVERSAL, pin=ev.get("pin"),
                        local_id=lid, synced_offline=True,
                    )
                results.append({"local_id": lid, "ok": r.get("ok", False), "msg": r.get("msg", "")})
            except Exception as e:
                results.append({"local_id": lid, "ok": False, "msg": f"Erro: {e}"})

        return {"ok": True, "results": results, "code": 200}

    @staticmethod
    def buscar_checkin_aberto(user):
        checkin = ServiceCheckin.query.filter_by(
            user_id=user.id, company_id=user.company_id, type="checkin"
        ).filter(ServiceCheckin.checkout_at == None).order_by(
            ServiceCheckin.id.desc()
        ).first()
        if not checkin:
            return {"open": False}
        client = Client.query.get(checkin.client_id)
        order  = Order.query.get(checkin.order_id) if checkin.order_id else None
        return {
            "open": True, "checkin_id": checkin.id, "checkin_at": checkin.checkin_at,
            "client_id": checkin.client_id, "client_name": client.name if client else "",
            "order_number": order.number if order else "", "order_id": checkin.order_id,
        }

    @staticmethod
    def gerar_url_qr_universal():
        return QR_CODE_UNIVERSAL

    @staticmethod
    def buscar_checkins_da_os(order_id, company_id):
        """Retorna todos os checkins de uma OS específica."""
        checkins = ServiceCheckin.query.filter_by(
            order_id=order_id, company_id=company_id, type="checkin"
        ).order_by(ServiceCheckin.id.desc()).all()
        return [c.to_dict() for c in checkins]