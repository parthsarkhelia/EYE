import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.secrets import secrets


def send_email(context: dict, subject: str, receiver_email: str, body: str):
    sender_email = secrets.get("smtp_sender_email")
    app_password = secrets.get("smtp_app_password")

    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP_SSL(
            secrets.get("smtp_host"), secrets.get("smtp_port")
        ) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        logging.info(
            {**context, "message": f"Email sent successfully to {receiver_email}"}
        )
    except Exception:
        logging.exception({**context, "message": "Error while sending email"})
