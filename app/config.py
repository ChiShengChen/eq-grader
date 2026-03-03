import os
from pathlib import Path
from dataclasses import dataclass, field

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # LLM
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5:14b"))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))

    # Database
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./eq_grader.db"))

    # Google OAuth
    google_client_id: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_ID", ""))
    google_client_secret: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_SECRET", ""))
    app_base_url: str = field(default_factory=lambda: os.getenv("APP_BASE_URL", "http://localhost:8000"))
    session_secret: str = field(default_factory=lambda: os.getenv("SESSION_SECRET", "change-me-to-a-random-string"))

    # Questionnaires
    questionnaires_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "questionnaires")
    questionnaires: dict = field(default_factory=dict)

    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    def load_questionnaires(self) -> None:
        self.questionnaires = {}
        for yaml_file in self.questionnaires_dir.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                self.questionnaires[config["id"]] = config


settings = Settings()
