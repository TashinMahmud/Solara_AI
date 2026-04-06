from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str
    internal_api_flights: str
    internal_api_hotels: str
    internal_api_submit: str
    app_env: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()
