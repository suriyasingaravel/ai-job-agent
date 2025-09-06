from typing import Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices as _Alias

def env_alias(*names: str): return _Alias(*names)

class Settings(BaseSettings):
    # LLM/embeddings (Gemini)
    google_api_key: Optional[str] = Field(
        default=None, validation_alias=env_alias("GOOGLE_API_KEY", "google_api_key")
    )
    gemini_embeddings_model: str = Field(
        default="models/embedding-001",
        validation_alias=env_alias("GEMINI_EMBEDDINGS_MODEL","gemini_embeddings_model"),
    )

    # External APIs (optional)
    serpapi_key: Optional[str] = Field(
        default=None, validation_alias=env_alias("SERPAPI_KEY","serpapi_key")
    )
    rocketreach_api_key: Optional[str] = Field(
        default=None, validation_alias=env_alias("ROCKETREACH_API_KEY","rocketreach_api_key")
    )

    # Storage
    data_dir: str = Field(default="./.data", validation_alias=env_alias("DATA_DIR","data_dir"))

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @model_validator(mode="after")
    def _validate(self):
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required")
        return self

settings = Settings()
