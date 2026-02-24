from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    GROQ_API_KEY: str
    GEMINI_API_KEY:str
    PINECONE_INDEX_NAME:str
    PINECONE_API_KEY:str
    

    class Config:
        env_file = ".env"

settings = Settings()
