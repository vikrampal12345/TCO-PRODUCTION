from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Copy Checker configuration namespaced away from other TCO settings."""

    app_name: str = "TCO Copy Checker"
    app_version: str = "0.2.0"

    upload_dir: str = "data/copy_checker/uploads"
    pages_dir: str = "data/copy_checker/pages"
    output_dir: str = "data/copy_checker/outputs"
    max_pdf_pages: int = 100

    model_provider: str = "lm_studio"
    vision_model_name: str = "qwen2.5-vl-3b-instruct"
    extraction_verifier_model_name: str = "qwen.qwen2.5-vl-3b-instruct"
    text_model_name: str = "qwen/qwen3-4b-2507"

    model_base_url: str = "http://127.0.0.1:1234/v1"
    model_api_key: str = "lm-studio"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="COPY_CHECKER_",
        extra="ignore",
    )


settings = Settings()
