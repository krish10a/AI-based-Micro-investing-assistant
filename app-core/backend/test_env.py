from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    nvidia_nim_api_key: str = Field(default="DEFAULT_KEY")
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

s = Settings()
print(f"Key length: {len(s.nvidia_nim_api_key)}")
print(f"Key starts with: {s.nvidia_nim_api_key[:10] if s.nvidia_nim_api_key else 'EMPTY'}")
print(f"Key ends with: {s.nvidia_nim_api_key[-10:] if s.nvidia_nim_api_key else 'EMPTY'}")
