import secrets
from datetime import datetime
from sqlalchemy import text
from costwise.models.license import License


class LicenseService:
    """Gerencia geração e validação de licenças Pro."""

    def __init__(self, db):
        self.db = db  # SQLAlchemy db de app.extensions

    def generate(self, email: str, plan: str, sale_id: str) -> License:
        """Gera nova chave, persiste no banco e retorna a License."""
        key = self._gerar_chave()
        now = datetime.utcnow()
        license = License(key=key, email=email, plan=plan,
                          gumroad_sale_id=sale_id, created_at=now)
        self._salvar(license)
        return license

    def validate(self, key: str) -> License | None:
        """Valida chave e retorna License se válida, None caso contrário."""
        row = self.db.session.execute(
            text("SELECT * FROM costwise_licenses WHERE key = :key"),
            {"key": key}
        ).mappings().first()

        if not row:
            return None

        license = License(
            key=row["key"],
            email=row["email"],
            plan=row["plan"],
            gumroad_sale_id=row["gumroad_sale_id"] or "",
            is_active=row["is_active"],
            activated_at=row["activated_at"],
            expires_at=row["expires_at"],
            created_at=row["created_at"],
        )
        return license if license.is_valid() else None

    def mark_activated(self, key: str) -> None:
        """Registra data de ativação da chave."""
        self.db.session.execute(
            text("UPDATE costwise_licenses SET activated_at = :now WHERE key = :key"),
            {"now": datetime.utcnow(), "key": key}
        )
        self.db.session.commit()

    def revoke(self, key: str) -> bool:
        """Revoga uma licença."""
        self.db.session.execute(
            text("UPDATE costwise_licenses SET is_active = FALSE WHERE key = :key"),
            {"key": key}
        )
        self.db.session.commit()
        return True

    def list_active(self) -> list[License]:
        """Retorna todas as licenças ativas."""
        rows = self.db.session.execute(
            text("SELECT * FROM costwise_licenses WHERE is_active = TRUE ORDER BY created_at DESC")
        ).mappings().all()
        return [License(**dict(r)) for r in rows]

    def _gerar_chave(self) -> str:
        """Gera chave no formato CW-PRO-XXXX-XXXX-XXXX."""
        partes = [secrets.token_hex(2).upper() for _ in range(3)]
        return f"CW-PRO-{'-'.join(partes)}"

    def _salvar(self, license: License) -> None:
        self.db.session.execute(text("""
            INSERT INTO costwise_licenses
                (key, email, plan, gumroad_sale_id, is_active, created_at)
            VALUES
                (:key, :email, :plan, :gumroad_sale_id, :is_active, :created_at)
        """), {
            "key":             license.key,
            "email":           license.email,
            "plan":            license.plan,
            "gumroad_sale_id": license.gumroad_sale_id,
            "is_active":       license.is_active,
            "created_at":      license.created_at,
        })
        self.db.session.commit()
