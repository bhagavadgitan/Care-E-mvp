"""Application configuration loaded from environment variables (fail-fast)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings:
    def __init__(self) -> None:
        # Required — fail fast if missing.
        self.MONGO_URL = os.environ["MONGO_URL"]
        self.DB_NAME = os.environ["DB_NAME"]
        self.JWT_SECRET = os.environ["JWT_SECRET"]
        self.ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
        self.ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

        # App metadata / optional config.
        self.API_VERSION = "1.0.0"
        self.ENV = os.environ.get("ENV", "development")
        self.DATA_MODE = "SYNTHETIC"
        self.cors_origins = [
            o.strip()
            for o in os.environ.get("CORS_ORIGINS", "*").split(",")
            if o.strip()
        ]

        # Auth config.
        self.EMERGENT_AUTH_BASE = os.environ.get(
            "EMERGENT_AUTH_BASE", "https://demobackend.emergentagent.com"
        )
        self.COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
        self.COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "none")
        self.ACCESS_TTL_MIN = 15
        self.REFRESH_TTL_DAYS = 7
        self.ONBOARDING_TTL_MIN = 20


settings = Settings()
