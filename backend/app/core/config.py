from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

class Settings(BaseSettings):

    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False

    DATABASE_URL: str = ""

    CHROMA_DIR: str = "./data/chroma"

    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10240

    GENERATED_OUTPUT_DIR: str = "output/generated"
    TEMPLATES_DIR: str = "./templates"

    MAX_CODE_REPAIR_ATTEMPTS: int = 3
    CODE_EXECUTION_TIMEOUT: int = 15
    SANDBOX_MEMORY_MB: int = 512
    SANDBOX_CPU_SECONDS: int = 10
    SANDBOX_CPU_LIMIT: float = 1.0
    SANDBOX_MAX_FILE_MB: int = 20
    SANDBOX_PREFER_DOCKER: bool = True

    ARTIFACTS_DIR: str = "data/artifacts"

    WORKSPACE_BASE_DIR: str = "./data/workspaces"
    WORKSPACE_CONTAINER_IMAGE: str = "kepler-sandbox:latest"
    WORKSPACE_IDLE_TTL_MINUTES: int = 30
    WORKSPACE_MEMORY_MB: int = 512
    WORKSPACE_CPU: float = 1.0
    ARTIFACT_TOKEN_EXPIRY_HOURS: int = 24
    INSTALL_TIMEOUT_SECONDS: int = 30
    APPROVED_ON_DEMAND: dict = {
        "seaborn": "0.13.2",
        "wordcloud": "1.9.3",
        "missingno": "0.5.2",
        "folium": "0.15.1",
        "altair": "5.2.0",
        "pyvis": "0.3.2",
    }

    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FILE_TOKEN_EXPIRE_MINUTES: int = 5

    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: Optional[str] = None
    COOKIE_NAME: str = "refresh_token"

    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    LLM_PROVIDER: str = "OLLAMA"
    OLLAMA_MODEL: str = "llama3"
    GOOGLE_MODEL: str = "models/gemini-2.5-flash"
    GOOGLE_API_KEY: str = ""
    NVIDIA_MODEL: str = "qwen/qwen3.5-397b-a17b"
    NVIDIA_API_KEY: str = ""
    MYOPENLM_MODEL: str = "default"
    MYOPENLM_API_URL: str = "https://openlmfallback-0adc8b183b77.herokuapp.com/api/chat"
    LLM_TIMEOUT: Optional[int] = None
    
    LLM_TEMPERATURE_STRUCTURED: float = 0.1
    LLM_TEMPERATURE_CHAT: float = 0.2
    LLM_TEMPERATURE_CREATIVE: float = 0.7
    LLM_TEMPERATURE_CODE: float = 0.1
    LLM_TOP_P_STRUCTURED: float = 0.9
    LLM_TOP_P_CHAT: float = 0.95
    LLM_MAX_TOKENS: int = 4000
    LLM_MAX_TOKENS_CHAT: int = 3000
    LLM_FREQUENCY_PENALTY: float = 0.0
    LLM_PRESENCE_PENALTY: float = 0.0
    LLM_TOP_K: int = 50

    MODELS_DIR: str = "./data/models"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_VERSION: str = "bge_m3_v1"
    EMBEDDING_DIMENSION: int = 1024
    
    RERANKER_MODEL: str = "BAAI/bge-reranker-large"
    USE_RERANKER: bool = True
    
    INITIAL_VECTOR_K: int = 80
    LEXICAL_K: int = 80
    LEXICAL_CANDIDATE_POOL: int = 2000
    RERANK_CANDIDATES_K: int = 30
    MMR_K: int = 30
    FINAL_K: int = 10
    MMR_LAMBDA: float = 0.5
    MAX_CONTEXT_TOKENS: int = 6000
    RAG_CONTEXT_MAX_TOKENS: int = 2000
    MIN_CHUNK_LENGTH: int = 100
    MIN_CONTEXT_CHUNK_LENGTH: int = 150
    MIN_SIMILARITY_SCORE: float = 0.5
    CHUNK_OVERLAP_TOKENS: int = 150

    OCR_TIMEOUT_SECONDS: int = 300
    WHISPER_TIMEOUT_SECONDS: int = 600
    LIBREOFFICE_TIMEOUT_SECONDS: int = 120
    PROCESSING_MAX_RETRIES: int = 2

    IMAGE_GENERATION_ENDPOINT: Optional[str] = None
    WEB_SEARCH_ENDPOINT: Optional[str] = None
    WEB_SCRAPE_ENDPOINT: Optional[str] = None
    WEB_IMAGE_SEARCH_ENDPOINT: Optional[str] = "http://16.16.144.216:8001/scrape"

    @field_validator("LLM_PROVIDER", mode="after")
    @classmethod
    def _uppercase_provider(cls, v: str) -> str:
        v = v.upper()
        valid = {"MYOPENLM", "GOOGLE", "NVIDIA", "OLLAMA"}
        if v not in valid:
            raise ValueError(f"LLM_PROVIDER must be one of {valid}, got {v!r}")
        return v

    @field_validator("JWT_SECRET_KEY", mode="after")
    @classmethod
    def _validate_jwt(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "JWT_SECRET_KEY must be set. "
                'Generate: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        return v

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def _validate_db_url(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "DATABASE_URL must be set. Example: postgresql://user:pass@localhost:5432/dbname"
            )
        return v

    @model_validator(mode="after")
    def _resolve_paths_and_cross_validate(self):
        for attr in ("CHROMA_DIR", "UPLOAD_DIR", "MODELS_DIR", "TEMPLATES_DIR",
                     "GENERATED_OUTPUT_DIR",
                     "WORKSPACE_BASE_DIR"):
            val = getattr(self, attr)
            if val and not os.path.isabs(val):
                object.__setattr__(self, attr, os.path.join(_PROJECT_ROOT, val))

        if self.ENVIRONMENT == "production":
            object.__setattr__(self, "COOKIE_SECURE", True)

        import logging
        _log = logging.getLogger("config")
        if self.LLM_PROVIDER == "GOOGLE" and not self.GOOGLE_API_KEY:
            _log.warning("LLM_PROVIDER is GOOGLE but GOOGLE_API_KEY is empty")
        if self.LLM_PROVIDER == "NVIDIA" and not self.NVIDIA_API_KEY:
            _log.warning("LLM_PROVIDER is NVIDIA but NVIDIA_API_KEY is empty")

        return self

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
