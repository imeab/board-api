from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경 변수(.env)에서 설정을 읽어옴"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://board:board@localhost:5432/board"
    jwt_secret_key: str  # 필수: 없으면 서버가 시작되지 않음
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    sql_echo: bool = False


settings = Settings()
