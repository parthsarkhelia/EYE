import logging

from src.core import send_email
from src.secrets import secrets


def send_user_verification_email(context: dict, receiver_email: str, token: str):
    try:
        # Replace placeholders as needed
        email_body = verification_email_body
        verification_url = (
            f"{secrets.get('website_user_email_verification_url')}?access_token={token}"
        )
        email_body = email_body.replace("[Your App Name]", secrets["app_name"])
        email_body = email_body.replace("YOUR_VERIFICATION_LINK_HERE", verification_url)

        email_subject = "Bureau EYE: Verify Your Email Address"
        send_email(context, email_subject, receiver_email, email_body)
        logging.info(
            {**context, "message": f"Verification email sent to {receiver_email}"}
        )
    except Exception:
        logging.exception(
            {**context, "message": "Error while sending verification email."}
        )


def send_org_verification_email(context: dict, receiver_email: str, token: str):
    try:
        # Replace placeholders as needed
        email_body = verification_email_body
        verification_url = (
            f"{secrets.get('website_org_email_verification_url')}?access_token={token}"
        )
        email_body = email_body.replace("[Your App Name]", secrets["app_name"])
        email_body = email_body.replace("YOUR_VERIFICATION_LINK_HERE", verification_url)

        email_subject = "Bureau EYE: Verify Your Email Address"
        send_email(context, email_subject, receiver_email, email_body)
        logging.info(
            {**context, "message": f"Verification email sent to {receiver_email}"}
        )
    except Exception:
        logging.exception(
            {**context, "message": "Error while sending verification email."}
        )


def send_reset_password_email(context: dict, receiver_email: str, token: str):
    try:
        email_body = reset_password_body

        # Replace placeholders as needed
        reset_url = f"{secrets.get('website_reset_password_url')}?access_token={token}"
        email_body = email_body.replace("YOUR_RESET_LINK_HERE", reset_url)

        email_subject = "Bureau EYE: Reset Your Password"
        send_email(context, email_subject, receiver_email, email_body)
        logging.info(
            {**context, "message": f"Reset email sent successfully to {receiver_email}"}
        )
    except Exception:
        logging.exception(
            {**context, "message": "Error while sending reset password email."}
        )


verification_email_body = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
            }

            .container {
                max-width: 600px;
                margin: 20px auto;
                padding: 20px;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
            }

            .button {
                background-color: white;
                border: none;
                font-weight: bold;
                padding: 10px 20px;
                display: block;
                margin: 20px auto;
                cursor: pointer;
                border-radius: 4px;
                border: 2px solid black;
                width: 25%

            }

            a {
                color: black;
                font-weight: bold;
                text-decoration: none;
                text-align: center;
                font-size: 16px;
            }

            h2 {
                color: blue;
                text-align: center;
            }

            p {
                color: black;
                text-align: center;
            }

        </style>
    </head>
    <body>

    <div class="container">
        <h2>Welcome to [Your App Name]!</h2>
        <p>
            Thanks for signing up for [Your App Name]. Before we get started, we need to verify your email address.
        </p>
        <a href="YOUR_VERIFICATION_LINK_HERE" class="button">Verify my email</a>
        <p>
            If you did not sign up for [Your App Name], you can safely ignore this email.
        </p>
    </div>

    </body>
    </html>
"""


reset_password_body = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
            }

            .container {
                max-width: 600px;
                margin: 20px auto;
                padding: 20px;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
            }

            .button {
                background-color: white;
                border: none;
                font-weight: bold;
                padding: 10px 20px;
                display: block;
                margin: 20px auto;
                cursor: pointer;
                border-radius: 4px;
                border: 2px solid black;
                width: 35%

            }

            a {
                color: black;
                font-weight: bold;
                text-decoration: none;
                text-align: center;
                font-size: 16px;
            }

            h2 {
                color: blue;
                text-align: center;
            }

            p {
                color: black;
                text-align: center;
            }

        </style>
    </head>
    <body>

    <div class="container">
        <h2>Reset Your Password</h2>
        <p>
            We received a request to reset the password for your Bureau EYE account.
        </p>
        <a href="YOUR_RESET_LINK_HERE" class="button">Reset My Password</a>
        <p>
            If you did not request a password reset, please ignore this email.<br>
            For security reasons, this link will expire in 24 hours.
        </p>
        <p>
            Warm Regards,<br>
            The Bureau EYE Team
        </p>
    </div>

    </body>
    </html>
"""
