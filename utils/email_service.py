import os
import secrets
from typing import Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Email configuration
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_FROM = os.getenv("MAIL_FROM", "noreply@toonzyai.me")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", "True").lower() == "true"
MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", "False").lower() == "true"

# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=MAIL_PORT,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_STARTTLS=MAIL_STARTTLS,      
    MAIL_SSL_TLS=MAIL_SSL_TLS,  
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

fastmail = FastMail(conf)

def generate_verification_token() -> str:
    """Generate a secure verification token."""
    return secrets.token_urlsafe(32)

async def send_verification_email(email: EmailStr, username: str, token: str) -> bool:
    """Send verification email to user."""
    try:
        # Frontend URL for verification
        frontend_url = os.getenv("FRONTEND_URL", "https://toonzyai.me")
        verification_url = f"{frontend_url}/verify-email?token={token}"
        
        message = MessageSchema(
            subject="Подтвердите ваш email - ToonzyAI",
            recipients=[email],
            body=f"""
            <html>
            <body>
                <h2>Добро пожаловать в ToonzyAI, {username}!</h2>
                <p>Для завершения регистрации подтвердите ваш email адрес.</p>
                <p>Нажмите на кнопку ниже для подтверждения:</p>
                <a href="{verification_url}" style="
                    display: inline-block;
                    background-color: #8b5cf6;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: bold;
                ">Подтвердить Email</a>
                <p>Или скопируйте эту ссылку в браузер:</p>
                <p>{verification_url}</p>
                <p>Если вы не регистрировались в ToonzyAI, проигнорируйте это письмо.</p>
                <p>С уважением,<br>Команда ToonzyAI</p>
            </body>
            </html>
            """,
            subtype="html"
        )
        
        await fastmail.send_message(message)
        logger.info(f"Verification email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {e}")
        return False

async def send_password_reset_email(email: EmailStr, username: str, token: str) -> bool:
    """Send password reset email to user."""
    try:
        frontend_url = os.getenv("FRONTEND_URL", "https://toonzyai.me")
        reset_url = f"{frontend_url}/reset-password?token={token}"
        
        message = MessageSchema(
            subject="Сброс пароля - ToonzyAI",
            recipients=[email],
            body=f"""
            <html>
            <body>
                <h2>Сброс пароля для {username}</h2>
                <p>Вы запросили сброс пароля для вашего аккаунта ToonzyAI.</p>
                <p>Нажмите на кнопку ниже для сброса пароля:</p>
                <a href="{reset_url}" style="
                    display: inline-block;
                    background-color: #ef4444;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: bold;
                ">Сбросить пароль</a>
                <p>Или скопируйте эту ссылку в браузер:</p>
                <p>{reset_url}</p>
                <p>Если вы не запрашивали сброс пароля, проигнорируйте это письмо.</p>
                <p>С уважением,<br>Команда ToonzyAI</p>
            </body>
            </html>
            """,
            subtype="html"
        )
        
        await fastmail.send_message(message)
        logger.info(f"Password reset email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        return False 