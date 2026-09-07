import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'brandcraft.db'}"
)

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "brandcraft-development-secret-key"
)

ALGORITHM = os.getenv("ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
)

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
HAS_GEMINI_KEY = bool(GEMINI_API_KEY)

HUGGINGFACE_API_KEY = os.getenv(
    "HUGGINGFACE_API_KEY",
    ""
).strip()

HAS_HF_KEY = bool(HUGGINGFACE_API_KEY)
HAS_HUGGINGFACE_KEY = HAS_HF_KEY

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "2525"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv(
    "SMTP_FROM",
    "noreply@brandcraft.ai"
)

SERVER_HOST = os.getenv(
    "SERVER_HOST",
    "http://127.0.0.1:8000"
)