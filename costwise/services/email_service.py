import os
import resend
from costwise.models.license import License

resend.api_key = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "noreply@svfinance.com.br")


class EmailService:
    """Envia emails transacionais do costwise via Resend."""

    def send_license(self, email: str, license: License) -> bool:
        """Envia email com a chave de licença após compra no Gumroad."""
        plano_label = "Lifetime" if license.plan == "lifetime" else "Monthly"
        corpo = f"""
        <div style="font-family:monospace;background:#0a0a0f;color:#e2e8f0;padding:32px;border-radius:8px;max-width:520px">
          <h2 style="color:#7c6af7;margin-bottom:8px">costwise — Licença Pro ativada</h2>
          <p style="color:#64748b;margin-bottom:24px">Obrigado pela compra! Sua chave está abaixo.</p>

          <div style="background:#1e1e2e;border:1px solid #7c6af7;border-radius:6px;padding:16px;margin-bottom:24px;text-align:center">
            <p style="color:#64748b;font-size:12px;margin-bottom:8px">SUA CHAVE DE LICENÇA</p>
            <p style="color:#7c6af7;font-size:18px;font-weight:bold;letter-spacing:2px">{license.key}</p>
          </div>

          <p style="color:#e2e8f0;margin-bottom:8px"><strong>Plano:</strong> Pro {plano_label}</p>

          <p style="color:#e2e8f0;margin-bottom:16px">Para ativar, execute no terminal:</p>
          <div style="background:#111118;border-radius:4px;padding:12px;font-size:13px;color:#38bdf8">
            costwise activate {license.key}
          </div>

          <hr style="border:none;border-top:1px solid #1e1e2e;margin:24px 0">
          <p style="color:#64748b;font-size:12px">
            Dúvidas? WhatsApp: +55 (44) 99116-6419<br>
            <a href="https://github.com/Salvatini95/costwise" style="color:#7c6af7">github.com/Salvatini95/costwise</a>
          </p>
        </div>
        """
        try:
            resend.Emails.send({
                "from":    f"costwise <{FROM_EMAIL}>",
                "to":      [email],
                "subject": f"Sua licença Pro costwise — {license.key}",
                "html":    corpo,
            })
            return True
        except Exception as e:
            print(f"[costwise] Erro ao enviar email para {email}: {e}")
            return False
