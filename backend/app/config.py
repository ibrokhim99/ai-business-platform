from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    environment: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Database
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "aibp"
    postgres_user: str = "aibp"
    postgres_password: str = "changeme"

    @property
    def database_url(self) -> str:
        return (f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}")

    @property
    def database_url_sync(self) -> str:
        return (f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}")

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Auth
    jwt_secret_key: str = "dev_secret_change_me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # MLflow
    mlflow_tracking_uri: str = "http://mlflow:5000"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "changeme"
    minio_bucket: str = "mlflow-artifacts"

    # LLM provider — "ollama" (default, local) or "openai"
    llm_provider: str = "ollama"

    # Ollama (local LLM)
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_timeout_s: int = 600
    ollama_num_ctx: int = 8192
    ollama_temperature: float = 0.4

    # OpenAI (used when llm_provider == "openai")
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    openai_timeout_s: int = 120
    openai_temperature: float = 0.4

    # Chat (LLM orchestration)
    chat_max_history_turns: int = 12
    chat_max_models_per_call: int = 10
    chat_model_concurrency: int = 4

    # Prediction cache TTL (seconds) per block
    cache_ttl_block_a: int = 21600   # 6h
    cache_ttl_block_b: int = 21600
    cache_ttl_block_c: int = 86400   # 24h
    cache_ttl_block_d: int = 21600
    cache_ttl_block_e: int = 21600
    cache_ttl_block_f: int = 900     # 15min
    cache_ttl_block_g: int = 21600
    cache_ttl_block_h: int = 21600   # marketing — 6h
    cache_ttl_block_i: int = 21600   # operations — 6h
    cache_ttl_block_j: int = 0       # fraud — never cache, always live


settings = Settings()
