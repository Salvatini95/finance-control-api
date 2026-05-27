# app/services/checkin_service.py
import math
from datetime import datetime, timezone
from app.extensions import db
from app.models import Client, Order, ServiceCheckin, User

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
    except:
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
        return token.strip() == QR_CODE_UNIVERSAL

    @staticmethod
    def validar_geolocalizacao(client, lat, lon, is_admin=False):
        if not client.latitude or not client.longitude:
            return {
                "ok": True,
                "distancia_metros": None,
                "msg": "⚠️ Cliente sem localização cadastrada — check-in liberado.",
                "sem_coordenadas": True,
            }
        if lat is None or lon is None:
            return {
                "ok": True,
                "distancia_metros": None,
                "msg": "⚠️ GPS não disponível — check-in registrado sem validação.",
                "sem_gps": True,
            }
        distancia = _haversine_metros(lat, lon, client.latitude, client.longitude)
        raio = RAIO_ADMIN_METROS if is_admin else RAIO_MAXIMO_METROS
        if distancia <= raio:
            return {"ok": True, "distancia_metros": round(distancia), "msg": f"📍 Localização confirmada ({round(distancia)}m)."}
        return {"ok": False, "distancia_metros": round(distancia),
                "msg": f"❌ Você está a {round(distancia)}m do cliente. Máximo permitido: {raio}m. Vá até o local e tente novamente."}

    @staticmethod
    def registrar_entrada(user, client_id, order_id, lat, lon, notes, qr_token):
        if qr_token and not CheckinService.validar_qr_universal(qr_token):
            return {"ok": False, "msg": "QR Code inválido.", "code": 400}

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

        geo = CheckinService.validar_geolocalizacao(client, lat, lon, is_admin=user.is_admin)
        if not geo["ok"]:
            return {"ok": False, "msg": geo["msg"], "distancia_metros": geo.get("distancia_metros"), "code": 400}

        if order and order.status == "open":
            order.status = "in_progress"

        now = _now()
        checkin = ServiceCheckin(
            client_id=client_id, user_id=user.id, company_id=user.company_id,
            order_id=order_id, executed_at=now, checkin_at=now,
            checkout_at=None, duration_min=None, type="checkin",
            latitude=lat, longitude=lon,
            notes=notes.strip() if notes else None,
        )
        db.session.add(checkin)
        db.session.commit()

        return {
            "ok": True, "msg": "✅ Check-in registrado!",
            "checkin_id": checkin.id, "checkin_at": checkin.checkin_at,
            "client_name": client.name, "order_id": order_id,
            "distancia_metros": geo.get("distancia_metros"),
            "geo_msg": geo["msg"], "code": 201,
        }

    @staticmethod
    def registrar_saida(user, checkin_id, lat, lon, notes, qr_token):
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
        if client:
            geo = CheckinService.validar_geolocalizacao(client, lat, lon, is_admin=user.is_admin)
            if not geo["ok"]:
                return {"ok": False, "msg": geo["msg"], "distancia_metros": geo.get("distancia_metros"), "code": 400}
        else:
            geo = {"msg": "GPS não validado.", "distancia_metros": None}

        now      = _now()
        duration = _diff_minutes(checkin.checkin_at, now)
        checkin.checkout_at  = now
        checkin.duration_min = duration
        if notes:
            checkin.notes = notes.strip()

        # ✅ Muda OS para "done" ao finalizar o check-out
        if checkin.order_id:
            order = Order.query.get(checkin.order_id)
            if order and order.status == "in_progress":
                order.status     = "done"
                from datetime import date
                order.finished_at = str(date.today())

        db.session.commit()

        h   = duration // 60 if duration else 0
        m   = duration % 60  if duration else 0
        dur_str = f"{h}h{m:02d}min" if h > 0 else f"{m}min"

        return {
            "ok": True, "msg": f"✅ Serviço concluído! Duração: {dur_str}",
            "checkin_id": checkin.id,
            "checkin_at": checkin.checkin_at,
            "checkout_at": checkin.checkout_at,
            "duration_min": duration,
            "duration_str": dur_str,
            "distancia_metros": geo.get("distancia_metros"),
            "order_status": "done",
            "code": 200,
        }

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
            "open": True,
            "checkin_id": checkin.id,
            "checkin_at": checkin.checkin_at,
            "client_id": checkin.client_id,
            "client_name": client.name if client else "",
            "order_number": order.number if order else "",
            "order_id": checkin.order_id,
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