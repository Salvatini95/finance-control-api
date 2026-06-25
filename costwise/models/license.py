from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class License:
    """Representa uma licença Pro do costwise."""
    key: str
    email: str
    plan: str                          # 'lifetime' | 'monthly'
    gumroad_sale_id: str
    is_active: bool = True
    activated_at: datetime = None
    expires_at: datetime = None        # None = lifetime
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "key":        self.key,
            "plan":       self.plan,
            "is_active":  self.is_active,
            "is_valid":   self.is_valid(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
