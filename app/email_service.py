import os
import resend

resend.api_key = os.environ.get("RESEND_API_KEY", "")

FROM_EMAIL   = os.environ.get("FROM_EMAIL", "noreply@svfinance.com.br")
FROM_NAME    = "SV Finance"
FROM_ADDR    = f"{FROM_NAME} <{FROM_EMAIL}>"


def _base_template(title, content, cta_url=None, cta_label=None):
    """Template base dark — alinhado com o visual do sistema."""
    cta_btn = ""
    if cta_url and cta_label:
        cta_btn = f"""
        <tr>
          <td align="center" style="padding: 8px 0 32px;">
            <a href="{cta_url}"
               style="display:inline-block; background:linear-gradient(135deg,#4f8ef7,#7c3aed);
                      color:#ffffff; text-decoration:none; font-size:15px; font-weight:700;
                      padding:14px 36px; border-radius:10px;
                      box-shadow:0 4px 20px rgba(79,142,247,0.4); letter-spacing:0.3px;">
              {cta_label}
            </a>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#080c14;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#080c14;padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="100%" style="max-width:560px;background:#0d1424;border-radius:20px;
               border:1px solid rgba(255,255,255,0.08);overflow:hidden;">

          <!-- HEADER -->
          <tr>
            <td style="background:linear-gradient(135deg,rgba(79,142,247,0.15),rgba(124,58,237,0.1));
                       padding:32px 40px 24px; border-bottom:1px solid rgba(255,255,255,0.08);">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <table cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="background:linear-gradient(135deg,#4f8ef7,#7c3aed);
                                   border-radius:10px;width:36px;height:36px;
                                   text-align:center;vertical-align:middle;font-size:18px;">
                          💎
                        </td>
                        <td style="padding-left:12px;font-size:18px;font-weight:700;
                                   color:#f0f4ff;letter-spacing:0.5px;">
                          SV Finance
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CONTEÚDO -->
          <tr>
            <td style="padding:36px 40px 8px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                {content}
                {cta_btn}
              </table>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="padding:24px 40px 32px;border-top:1px solid rgba(255,255,255,0.06);">
              <p style="margin:0;font-size:12px;color:#6b7fa3;line-height:1.6;">
                Este email foi enviado pelo <strong style="color:#94a3b8;">SV Finance</strong>.
                Se você não solicitou esta ação, pode ignorar este email com segurança.<br/>
                <a href="https://svfinance.com.br" style="color:#4f8ef7;text-decoration:none;">svfinance.com.br</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_verification_email(to_email: str, name: str, token: str, app_url: str = "https://svfinance.com.br"):
    verify_url = f"{app_url}/verify-email?token={token}"

    content = f"""
    <tr>
      <td style="padding-bottom:8px;">
        <h1 style="margin:0;font-size:24px;font-weight:700;color:#f0f4ff;letter-spacing:-0.5px;">
          Confirme seu email 📧
        </h1>
      </td>
    </tr>
    <tr>
      <td style="padding-bottom:24px;">
        <p style="margin:0;font-size:15px;color:#94a3b8;line-height:1.7;">
          Olá, <strong style="color:#f0f4ff;">{name}</strong>! 👋<br/><br/>
          Bem-vindo ao <strong style="color:#4f8ef7;">SV Finance</strong>. Sua conta foi criada com sucesso.
          Clique no botão abaixo para verificar seu email e começar a usar o sistema.
        </p>
      </td>
    </tr>
    <tr>
      <td style="padding-bottom:24px;">
        <div style="background:rgba(79,142,247,0.08);border:1px solid rgba(79,142,247,0.2);
                    border-radius:10px;padding:16px 20px;">
          <p style="margin:0;font-size:12px;color:#6b7fa3;">Link de verificação</p>
          <p style="margin:6px 0 0;font-size:13px;color:#4f8ef7;word-break:break-all;">
            {verify_url}
          </p>
        </div>
      </td>
    </tr>
    <tr>
      <td style="padding-bottom:16px;">
        <p style="margin:0;font-size:13px;color:#6b7fa3;">
          ⏱ Este link expira em <strong style="color:#94a3b8;">24 horas</strong>.
        </p>
      </td>
    </tr>
    """

    html = _base_template(
        title     = "Confirme seu email — SV Finance",
        content   = content,
        cta_url   = verify_url,
        cta_label = "Verificar meu email →",
    )

    resend.Emails.send({
        "from":    FROM_ADDR,
        "to":      [to_email],
        "subject": "Confirme seu email — SV Finance",
        "html":    html,
    })


def send_password_reset_email(to_email: str, name: str, token: str, app_url: str = "https://svfinance.com.br"):
    reset_url = f"{app_url}/reset-password?token={token}"

    content = f"""
    <tr>
      <td style="padding-bottom:8px;">
        <h1 style="margin:0;font-size:24px;font-weight:700;color:#f0f4ff;letter-spacing:-0.5px;">
          Redefinir senha 🔐
        </h1>
      </td>
    </tr>
    <tr>
      <td style="padding-bottom:24px;">
        <p style="margin:0;font-size:15px;color:#94a3b8;line-height:1.7;">
          Olá, <strong style="color:#f0f4ff;">{name}</strong>!<br/><br/>
          Recebemos uma solicitação para redefinir a senha da sua conta no
          <strong style="color:#4f8ef7;">SV Finance</strong>.
          Clique no botão abaixo para criar uma nova senha.
        </p>
      </td>
    </tr>
    <tr>
      <td style="padding-bottom:24px;">
        <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);
                    border-radius:10px;padding:16px 20px;">
          <p style="margin:0;font-size:13px;color:#f87171;">
            ⚠️ Se você não solicitou a redefinição de senha, ignore este email.
            Sua senha permanece a mesma.
          </p>
        </div>
      </td>
    </tr>
    <tr>
      <td style="padding-bottom:16px;">
        <p style="margin:0;font-size:13px;color:#6b7fa3;">
          ⏱ Este link expira em <strong style="color:#94a3b8;">1 hora</strong>.
        </p>
      </td>
    </tr>
    """

    html = _base_template(
        title     = "Redefinir senha — SV Finance",
        content   = content,
        cta_url   = reset_url,
        cta_label = "Redefinir minha senha →",
    )

    resend.Emails.send({
        "from":    FROM_ADDR,
        "to":      [to_email],
        "subject": "Redefinir senha — SV Finance",
        "html":    html,
    })