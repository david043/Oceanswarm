from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = ""

    tick_interval_seconds: int = 30
    world_width: int = 100
    world_height: int = 100
    interaction_radius: int = 5
    max_agent_memory: int = 10

    database_url: str = "sqlite+aiosqlite:///./oceanswarm.db"

    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
