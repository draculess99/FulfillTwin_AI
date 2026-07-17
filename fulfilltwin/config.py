from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

PACKAGE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = PACKAGE_DIR / "backend"
DATA_DIR = BACKEND_DIR / "data"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
STORAGE_DIR = BACKEND_DIR / "storage"
ARTIFACT_DIR = BACKEND_DIR / "artifacts"


@dataclass(frozen=True)
class Settings:
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "5000"))
    api_url: str = os.getenv("FULFILLTWIN_API_URL", "http://127.0.0.1:5000")
    memory_file: Path = Path(os.getenv("MEMORY_FILE", str(STORAGE_DIR / "memory.json")))
    max_memory_records: int = int(os.getenv("MAX_MEMORY_RECORDS", "250"))
    model_seed: int = int(os.getenv("MODEL_SEED", "42"))
    training_rows: int = int(os.getenv("TRAINING_ROWS", "3500"))
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    groq_models: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv(
            "GROQ_MODELS",
            "llama-3.3-70b-versatile,openai/gpt-oss-20b,moonshotai/kimi-k2-instruct",
        ).split(",")
        if item.strip()
    )
    gemini_models: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv(
            "GEMINI_MODELS",
            "gemini-3.5-flash,gemini-2.5-flash-lite,gemini-2.5-pro",
        ).split(",")
        if item.strip()
    )

    def ensure_directories(self) -> None:
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
