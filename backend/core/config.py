from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    groq_api_key: str = ""
    openrouter_api_key: str = ""
    database_url: str = "postgresql+asyncpg://postgres:lifeos@localhost:5433/lifeos"

    @property
    def async_database_url(self) -> str:
        """Ensure DATABASE_URL uses asyncpg driver (Railway provides postgresql://)."""
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    redis_url: str = "redis://localhost:6379"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_auth_token: str = ""  # Auth proxy API key (if using Railway auth proxy)
    tavily_api_key: str = ""
    environment: str = "development"
    debug: bool = False

    # URLs — configurable for deployment
    frontend_url: str = "http://localhost:3002"
    backend_url: str = "http://localhost:8001"

    # Clerk authentication
    clerk_jwks_url: str = ""
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    clerk_webhook_secret: str = ""

    # S3-compatible storage (Cloudflare R2, AWS S3, MinIO, etc.)
    s3_bucket_name: str = ""
    s3_endpoint_url: str = ""  # e.g. https://<account>.r2.cloudflarestorage.com
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_region: str = "auto"  # R2 uses "auto"

    # Encryption for user API keys
    encryption_key: str = ""  # Fernet key — generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    # Google OAuth (Gmail integration)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8001/integrations/gmail/callback"

    # CORS — derives from frontend_url by default
    allowed_origins: list[str] = ["http://localhost:3002"]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
