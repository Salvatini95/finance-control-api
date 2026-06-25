from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PingEvent:
    """Evento de telemetria anônima do costwise."""
    install_id: str
    version: str
    days_remaining: int
    is_pro: bool
    platform: str         # 'linux' | 'macos' | 'wsl2'
    project_count: int
    tokens_range: str     # '<1M' | '1-10M' | '10-100M' | '>100M'
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "install_id":     self.install_id,
            "version":        self.version,
            "days_remaining": self.days_remaining,
            "is_pro":         self.is_pro,
            "platform":       self.platform,
            "project_count":  self.project_count,
            "tokens_range":   self.tokens_range,
        }
