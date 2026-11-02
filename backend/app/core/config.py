"""Application settings. All secrets live here (backend only) and are never serialised to clients."""
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent          # backend/app
PROJECT_DIR = BASE_DIR.parent.parent                       # repo root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    database_url: SecretStr = SecretStr("sqlite:///./farmshield.db")
    session_secret: Optional[SecretStr] = None

    # --- weather (Open-Meteo) ---
    open_meteo_base_url: str = "https://api.open-meteo.com"
    open_meteo_geocoding_url: str = "https://geocoding-api.open-meteo.com"
    open_meteo_archive_url: str = "https://archive-api.open-meteo.com"
    weather_fresh_minutes: int = 60          # configurable freshness policy (L4)
    weather_stale_minutes: int = 360
    weather_cache_seconds: int = 600
    provider_timeout_seconds: float = 12.0
    provider_max_retries: int = 2

    # --- IMD (optional; only if a verified feed exists) ---
    imd_api_base_url: Optional[str] = None
    imd_api_key: Optional[SecretStr] = None
    imd_cap_feed_url: Optional[str] = None
    imd_fresh_minutes: int = 180

    # --- LLM ---
    llm_provider: str = "disabled"           # disabled | anthropic | openai_compatible
    llm_api_key: Optional[SecretStr] = None
    llm_model: str = ""
    llm_base_url: Optional[str] = None
    llm_timeout_seconds: float = 40.0

    # --- risk engine ---
    allow_unverified_rules: bool = False     # keep False in production (spec: never invent thresholds)

    # --- Level 3 ---
    data_gov_in_api_key: Optional[SecretStr] = None
    agmarknet_resource_id: Optional[str] = None
    data_gov_in_base_url: str = "https://api.data.gov.in"
    satellite_provider: str = "modis_ornl"   # modis_ornl | disabled
    modis_base_url: str = "https://modis.ornl.gov/rst/api/v1"
    stt_api_base_url: Optional[str] = None
    stt_api_key: Optional[SecretStr] = None
    stt_model: str = "whisper-1"
    admin_api_token: Optional[SecretStr] = None

    # --- limits ---
    max_body_bytes: int = 11 * 1024 * 1024   # 10 MB image + multipart overhead
    max_image_bytes: int = 10 * 1024 * 1024
    rate_limit_per_minute: int = 120
    rate_limit_ai_per_minute: int = 12

    @field_validator("cors_origins")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def secret(self, name: str) -> Optional[str]:
        v = getattr(self, name, None)
        return v.get_secret_value() if v is not None else None

    @property
    def llm_configured(self) -> bool:
        return self.llm_configuration_status == "configured_not_tested"

    @property
    def llm_status(self) -> str:
        configured = self.llm_configuration_status
        if configured != "configured_not_tested":
            return configured
        from .monitoring import status_for
        return {"unknown": "configured_not_tested", "available": "operational",
                "unavailable": "temporarily_unavailable"}.get(status_for("llm"), "configured_not_tested")

    @property
    def llm_configuration_status(self) -> str:
        if self.llm_provider == "disabled":
            return "not_configured"
        if self.llm_provider not in {"anthropic", "openai_compatible"}:
            return "invalid_configuration"
        api_key = self.secret("llm_api_key")
        if not api_key or not api_key.strip() or not self.llm_model:
            return "not_configured"
        if (any(char.isspace() or ord(char) < 32 for char in api_key)
                or api_key.strip().lower() in {"your-api-key", "replace-me", "changeme", "placeholder"}):
            return "invalid_configuration"
        if (not self.llm_model.strip() or len(self.llm_model) > 200
                or any(char.isspace() or ord(char) < 32 for char in self.llm_model)
                or self.llm_model.lower() in {"your-model", "model-name", "replace-me"}):
            return "invalid_configuration"
        if self.llm_base_url:
            from urllib.parse import urlsplit
            try:
                url = urlsplit(self.llm_base_url)
                host = url.hostname
                port = url.port
            except ValueError:
                return "invalid_configuration"
            local_host = host in {"localhost", "127.0.0.1", "::1"} if host else False
            if (url.scheme != "https" and not (self.app_env != "production" and url.scheme == "http" and local_host)):
                return "invalid_configuration"
            if not host or url.username or url.password or url.query or url.fragment or port == 0:
                return "invalid_configuration"
        if self.llm_provider == "openai_compatible" and not self.llm_base_url:
            return "not_configured"
        return "configured_not_tested"


@lru_cache
def get_settings() -> Settings:
    return Settings()
