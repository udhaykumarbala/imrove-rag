from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # OPENAI_API_KEY: str
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str
    MONGODB_URL: str
    MONGO_DATABASE: str
    JWT_SECRET_KEY: str
    MAILERSEND_API_KEY: str
    # JWT_EXPIRY_DAYS: int = 30
    # SENDGRID_API_KEY: str
    # SENDGRID_FROM_EMAIL: str
    XAI_API_KEY: str
    class Config:
        env_file = ".env"

settings = Settings()
