from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    CLAIM_MIN_PERCENT: int = 75
    CLAIM_RETRY_COUNT: int = 3

    UPGRADE_SPEED: bool = True
    SPEED_MAX_LEVEL: int = 7

    UPGRADE_STORAGE: bool = True
    STORAGE_MAX_LEVEL: int = 7

    DEFAULT_SLEEP: int = 3600

    USE_PROXY_FROM_FILE: bool = False


settings = Settings()
