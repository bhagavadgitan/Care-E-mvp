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
        # App metadata / optional config.
        self.API_VERSION = "1.0.0"
        self.ENV = os.environ.get("ENV", "development")
        self.DATA_MODE = "SYNTHETIC"
        self.cors_origins = [
            o.strip()
            for o in os.environ.get("CORS_ORIGINS", "*").split(",")
            if o.strip()
        ]


settings = Settings()
