import smtplib
from email.message import EmailMessage

from config import DEV_EXPOSE_OTP, SMTP_FROM, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER


def send_otp_email(to_email: str, otp: str, purpose: str) -> dict:
    subject = "FasTradeX verification code"
    if purpose == "reset_password":
        subject = "FasTradeX password reset code"
    body = f"Your FasTradeX OTP is {otp}. It expires in 10 minutes.\n\nEducational tool only — not investment advice."

    if not SMTP_USER or not SMTP_PASS:
        return {"sent": False, "dev_otp": otp if DEV_EXPOSE_OTP else None}

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    return {"sent": True}
