import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# System constants
MAX_RETRIES: int = 3
DEFAULT_MODEL: str = "llama-3.3-70b-versatile"
TOP_K: int = 5

# Latency optimization options
EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "4096"))
EMBEDDING_TRUNCATE: bool = os.getenv("EMBEDDING_TRUNCATE", "false").lower() in ("true", "1")
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
RAG_MIN_SIMILARITY: float = float(os.getenv("RAG_MIN_SIMILARITY", "0.3"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(env_path),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys
    GROQ_API_KEY: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    NVIDIA_API_KEY: str = Field(default_factory=lambda: os.getenv("NVIDIA_API_KEY", ""))

    # PostgreSQL configuration (for Day 2 RAG)
    POSTGRES_HOST: str = Field(default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"))
    POSTGRES_PORT: int = Field(default_factory=lambda: int(os.getenv("POSTGRES_PORT", "5432")))
    POSTGRES_MAINTAINANCE_DB: str = Field(
        default_factory=lambda: os.getenv("POSTGRES_MAINTAINANCE_DB", "postgres")
    )
    POSTGRES_USERNAME: str = Field(
        default_factory=lambda: os.getenv("POSTGRES_USERNAME", "postgres")
    )
    POSTGRES_PASSWORD: str = Field(default_factory=lambda: os.getenv("POSTGRES_PASSWORD", ""))

    # Constants exposed on settings
    max_retries: int = MAX_RETRIES
    default_model: str = DEFAULT_MODEL
    top_k: int = TOP_K

    # Latency optimization options
    embedding_dim: int = EMBEDDING_DIM
    embedding_truncate: bool = EMBEDDING_TRUNCATE
    rag_top_k: int = RAG_TOP_K
    rag_min_similarity: float = RAG_MIN_SIMILARITY


settings = Settings()

# Direct constant exports
GROQ_API_KEY = settings.GROQ_API_KEY
NVIDIA_API_KEY = settings.NVIDIA_API_KEY
POSTGRES_HOST = settings.POSTGRES_HOST
POSTGRES_PORT = settings.POSTGRES_PORT
POSTGRES_MAINTAINANCE_DB = settings.POSTGRES_MAINTAINANCE_DB
POSTGRES_USERNAME = settings.POSTGRES_USERNAME
POSTGRES_PASSWORD = settings.POSTGRES_PASSWORD
EMBEDDING_DIM = settings.embedding_dim
EMBEDDING_TRUNCATE = settings.embedding_truncate
RAG_TOP_K = settings.rag_top_k
RAG_MIN_SIMILARITY = settings.rag_min_similarity
