from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # NVIDIA NIM API
    nvidia_nim_api_key: str = Field(default="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")
    nvidia_nim_base_url: str = Field(default="https://integrate.api.nvidia.com/v1")

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # ML Artifacts
    artifacts_dir: str = Field(default="./artifacts")

    # Logging
    log_level: str = Field(default="INFO")

    # NVIDIA NIM config - Updated to match working test config
    nim_model: str = Field(default="meta/llama-3.1-70b-instruct")
    nim_temperature: float = Field(default=0.7)  # Match working NIM config
    nim_top_p: float = Field(default=0.9)        # Match working NIM config
    nim_max_tokens: int = Field(default=512)     # Reduced for faster response

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )


settings = Settings()
