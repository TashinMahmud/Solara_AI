from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str
    internal_api_flights: str
    internal_api_hotels: str
    internal_api_submit: str
    internal_api_cancellation: str = ""
    internal_api_loyalty: str = ""
    internal_api_pricing: str = ""
    app_env: str = "development"
    tripadvisor_api_key: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
