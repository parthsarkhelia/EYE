import logging
import os

from dotenv import load_dotenv

load_dotenv()

secrets = None


def get_secrets():
    env = os.environ.get("ENV", "")
    logging.info(f"Env: {env}")
    if env not in ["local", "dev", "prd"]:
        return {}

    # Environment Secrets
    # Assume Heroku production environment
    secrets_data = {
        "logging_level": os.environ.get("LOGGING_LEVEL", "INFO"),
        "app_name": os.environ.get("APP_NAME"),
        # JWT Variable
        "jwt_secret_key": os.environ.get("SECRET_KEY"),
        "jwt_encode_algorithm": os.environ.get("JWT_ENCODE_ALGORITHM"),
        "jwt_token_expiry": int(os.environ.get("JWT_TOKEN_EXPIRY")),
        "reset_token_expiry": int(os.environ.get("RESET_TOKEN_EXPIRY")),
        # SMTP Variable
        "smtp_host": os.environ.get("SMTP_HOST"),
        "smtp_port": os.environ.get("SMTP_PORT"),
        "smtp_sender_email": os.environ.get("SMTP_SENDER_EMAIL"),
        "smtp_app_password": os.environ.get("SMTP_APP_PASSWORD"),
        # Database Variable
        "mongodb_conn_string": os.environ.get("MONGODB_CONN_STRING"),
        "db_name": os.environ.get("DB_NAME"),
        "user_collection": os.environ.get("USER_COLLECTION"),
        "social_auth_collection": os.environ.get("SOCIAL_AUTH_COLLECTION"),
        "email_analysis_collection": os.environ.get("EMAIL_ANALYSIS_COLLECTION"),
        # Social Auths Variable
        "social_auth_redirection_url": os.environ.get("SOCIAL_AUTH_REDIRECTION_URL"),
        "google_client_id": os.environ.get("GOOGLE_CLIENT_ID"),
        "google_client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
        "google_authentication_url": os.environ.get("GOOGLE_AUTHENTICATION_URL"),
        "google_redirect_uri": os.environ.get("GOOGLE_REDIRECT_URI"),
        "google_token_url": os.environ.get("GOOGLE_TOKEN_URL"),
        "google_user_info_url": os.environ.get("GOOGLE_USER_INFO_URL"),
        
        # Device Auth Keys
        "authorization_key": os.environ.get("AUTHORIZATION_KEY")
    }
    return secrets_data


if not secrets:
    try:
        secrets = get_secrets()
    except Exception as e:
        logging.error(f"Error secret: {e}")
