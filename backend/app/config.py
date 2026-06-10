import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./brandcraft.db")

# JWT authentication settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-brandcraft-signing-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day (accommodates remember-me user sessions)
REFRESH_TOKEN_EXPIRE_DAYS = 7

# SMTP Email configurations
SMTP_HOST = os.getenv("SMTP_HOST", "sandbox.smtp.mailtrap.io")
SMTP_PORT = int(os.getenv("SMTP_PORT", "2525"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@brandcraft.ai")

# AI Services keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

# Directory configurations
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Feature flags for fallback modes
HAS_GEMINI_KEY = bool(GEMINI_API_KEY)
HAS_HF_KEY = bool(HUGGINGFACE_API_KEY)

# Server details for verification links
SERVER_HOST = os.getenv("SERVER_HOST", "http://127.0.0.1:8000")
