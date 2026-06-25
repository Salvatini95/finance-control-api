import hashlib
import hmac
import os


WEBHOOK_SECRET = os.environ.get("COSTWISE_WEBHOOK_SECRET", "")


class WebhookService:
    """Valida e processa webhooks do Gumroad."""

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verifica assinatura HMAC-SHA256 do Gumroad.
        Header: X-Gumroad-Signature
        """
        if not WEBHOOK_SECRET or not signature:
            return False
        expected = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_gumroad_payload(self, form_data: dict) -> dict:
        """Extrai campos relevantes do payload do Gumroad."""
        return {
            "email":        form_data.get("email", "").strip().lower(),
            "sale_id":      form_data.get("sale_id", ""),
            "product_name": form_data.get("product_name", ""),
            "price":        int(form_data.get("price", 0) or 0),  # centavos
            "refunded":     form_data.get("refunded", "false") == "true",
            "test":         form_data.get("test", "false") == "true",
            "recurrence":   form_data.get("recurrence", ""),
        }

    def determinar_plano(self, dados: dict) -> str:
        """Determina plano (lifetime/monthly) a partir do payload."""
        if dados.get("recurrence") in ("monthly", "yearly"):
            return "monthly"
        return "lifetime"
