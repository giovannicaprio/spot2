from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Spot2 Real Estate Chatbot"
    
    # Google AI Settings
    GOOGLE_API_KEY: str
    
    # Model Settings
    MODEL_NAME: str = "gemini-1.5-flash"


    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings() 