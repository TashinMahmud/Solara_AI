from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./chatbot_new.db")
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key")
    claude_api_key: str = os.getenv("CLAUDE_API_KEY", "your-claude-api-key-here")

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()