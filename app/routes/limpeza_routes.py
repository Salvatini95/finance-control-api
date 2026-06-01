# ── MODELOS RESTAURA GLASS (isolados, não afetam outros nichos) ──────────────

from sqlalchemy.dialects.postgresql import JSON as PGJSON

class LimpezaServiceCard(db.Model):
    __tablename__ = "limpeza_service_cards"

    id           = db.Column(db.Integer, primary_key=True)
    company_id   = db.Column(db.Integer, nullable=False, index=True)
    order_id     = db.Column(db.Integer, nullable=False, unique=True, index=True)
    client_id    = db.Column(db.Integer, nullable=False, server_default="0")
    frequencia   = db.Column(db.String(20), nullable=False, server_default="semanal")
    mes          = db.Column(db.Integer, nullable=False, server_default="1")
    ano          = db.Column(db.Integer, nullable=False, server_default="2024")
    dias_semana  = db.Column(db.String(3), nullable=False, server_default="seg")
    obs_contrato = db.Column(db.String(255), nullable=True)
    semanas      = db.Column(PGJSON, nullable=False, server_default="[]")
    created_at   = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at   = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())

    def to_dict(self):
        return {
            "id": self.id, "company_id": self.company_id, "order_id": self.order_id,
            "client_id": self.client_id, "frequencia": self.frequencia, "mes": self.mes,
            "ano": self.ano, "dias_semana": self.dias_semana, "obs_contrato": self.obs_contrato,
            "semanas": self.semanas or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class LimpezaOccurrence(db.Model):
    __tablename__ = "limpeza_occurrences"

    id                 = db.Column(db.Integer, primary_key=True)
    company_id         = db.Column(db.Integer, nullable=False, index=True)
    order_id           = db.Column(db.Integer, nullable=False, index=True)
    user_id            = db.Column(db.Integer, nullable=True)
    tipo               = db.Column(db.String(30), nullable=False, server_default="")
    data               = db.Column(db.String(10), nullable=False, server_default="")
    hora               = db.Column(db.String(5), nullable=True)
    reagendamento_data = db.Column(db.String(10), nullable=True)
    reagendamento_hora = db.Column(db.String(5), nullable=True)
    descricao          = db.Column(db.Text, nullable=True)
    created_at         = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id, "company_id": self.company_id, "order_id": self.order_id,
            "user_id": self.user_id, "tipo": self.tipo, "data": self.data, "hora": self.hora,
            "reagendamento_data": self.reagendamento_data, "reagendamento_hora": self.reagendamento_hora,
            "descricao": self.descricao,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }