import os
os.environ["RESEND_API_KEY"] = "re_WFgXh2fs_Aqo7tFquscU1DksPEWXoAwYf"

from app.email_service import send_verification_email

result = send_verification_email(
    to_email="salvatiniguilherme@gmail.com",
    name="Guilherme",
    token="token-de-teste-123"
)
print("Enviado!" if result else "Erro!")