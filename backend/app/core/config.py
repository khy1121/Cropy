from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "CropCare AI"
    app_version: str = "1.0.0"
    database_url: str = "sqlite:///./cropcare.db"
    upload_dir: Path = Path("./uploads")
    ml_model_path: Path = Path("../ml/checkpoints/best_model.pth")
    cors_origins: str = "http://localhost:3000"
    max_upload_mb: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
