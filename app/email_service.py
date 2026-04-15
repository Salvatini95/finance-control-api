import resend
import os

# 🔐 API KEY
resend.api_key = os.environ.get("RESEND_API_KEY")
print("API KEY:", resend.api_key)
# ✅ FORÇA EMAIL DE TESTE (IMPORTANTE PRO RESEND FUNCIONAR)
FROM_EMAIL = "onboarding@resend.dev"

# 🌐 FRONTEND URL
APP_URL = os.environ.get(
    "APP_URL",
    "https://finance-control-web-five.vercel.app"
)


# =========================
# EMAIL DE VERIFICAÇÃO
# =========================
def send_verification_email(to_email: str, name: str, token: str):
    verify_url = f"{APP_URL}/verify-email?token={token}"

    print("📩 ENVIANDO EMAIL DE VERIFICAÇÃO")
    print("TO:", to_email)
    print("FROM:", FROM_EMAIL)

    try:
        response = resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "✅ Confirme seu email — SV Finance Control",
            "html": f"""
            <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;background:#0f172a;color:#fff;border-radius:16px;overflow:hidden">
              <div style="background:linear-gradient(135deg,#6366f1,#4f46e5);padding:32px;text-align:center">
                <h1 style="margin:0;font-size:24px;letter-spacing:2px">FINANCE CONTROL</h1>
                <p style="margin:8px 0 0;opacity:0.8;font-size:13px">Gerencie suas finanças com inteligência</p>
              </div>
              <div style="padding:32px">
                <h2 style="color:#fff;margin:0 0 12px">Olá, {name}! 👋</h2>
                <p style="color:#94a3b8;line-height:1.6">Obrigado por criar sua conta no SV Finance Control. Clique no botão abaixo para confirmar seu email e ativar sua conta.</p>
                <div style="text-align:center;margin:32px 0">
                  <a href="{verify_url}" style="background:linear-gradient(135deg,#6366f1,#4f46e5);color:#fff;padding:14px 32px;border-radius:50px;text-decoration:none;font-weight:700;font-size:15px;display:inline-block">
                    ✅ Confirmar Email
                  </a>
                </div>
                <p style="color:#64748b;font-size:12px;text-align:center">
                  Este link expira em <strong style="color:#94a3b8">24 horas</strong>.<br>
                  Se não criou uma conta, ignore este email.
                </p>
                <div style="background:#1e293b;border-radius:8px;padding:12px 16px;margin-top:20px">
                  <p style="color:#64748b;font-size:11px;margin:0">Ou copie e cole este link no navegador:</p>
                  <p style="color:#6366f1;font-size:11px;margin:4px 0 0;word-break:break-all">{verify_url}</p>
                </div>
              </div>
              <div style="padding:20px 32px;border-top:1px solid #1e293b;text-align:center">
                <p style="color:#475569;font-size:12px;margin:0">SV Finance Control · svfinance.com.br</p>
              </div>
            </div>
            """,
        })

        print("✅ RESEND RESPONSE:", response)
        return True

    except Exception as e:
        import traceback
        print("❌ ERRO COMPLETO EMAIL:")
        traceback.print_exc()
        return False


# =========================
# RESET DE SENHA
# =========================
def send_password_reset_email(to_email: str, name: str, token: str):
    reset_url = f"{APP_URL}/reset-password?token={token}"

    print("📩 ENVIANDO EMAIL DE RESET")
    print("TO:", to_email)
    print("FROM:", FROM_EMAIL)

    try:
        response = resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "🔑 Redefinir senha — SV Finance Control",
            "html": f"""
            <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;background:#0f172a;color:#fff;border-radius:16px;overflow:hidden">
              <div style="background:linear-gradient(135deg,#f59e0b,#d97706);padding:32px;text-align:center">
                <h1 style="margin:0;font-size:24px;letter-spacing:2px">FINANCE CONTROL</h1>
                <p style="margin:8px 0 0;opacity:0.8;font-size:13px">Redefinição de senha</p>
              </div>
              <div style="padding:32px">
                <h2 style="color:#fff;margin:0 0 12px">Olá, {name}! 🔑</h2>
                <p style="color:#94a3b8;line-height:1.6">Recebemos uma solicitação para redefinir a senha da sua conta.</p>
                <div style="text-align:center;margin:32px 0">
                  <a href="{reset_url}" style="background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;padding:14px 32px;border-radius:50px;text-decoration:none;font-weight:700;font-size:15px;display:inline-block">
                    🔑 Redefinir Senha
                  </a>
                </div>
                <p style="color:#64748b;font-size:12px;text-align:center">
                  Este link expira em <strong style="color:#94a3b8">1 hora</strong>.<br>
                  Se não solicitou, ignore este email.
                </p>
              </div>
              <div style="padding:20px 32px;border-top:1px solid #1e293b;text-align:center">
                <p style="color:#475569;font-size:12px;margin:0">SV Finance Control · svfinance.com.br</p>
              </div>
            </div>
            """,
        })

        print("✅ RESEND RESPONSE:", response)
        return True

    except Exception as e:
        import traceback
        print("❌ ERRO COMPLETO RESET:")
        traceback.print_exc()
        return False
