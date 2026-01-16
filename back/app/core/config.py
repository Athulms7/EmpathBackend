from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    OPENROUTER_API_KEY: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
