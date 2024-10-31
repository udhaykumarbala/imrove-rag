from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    REDIS_HOST: str = "redis-13506.c322.us-east-1-2.ec2.redns.redis-cloud.com"
    REDIS_PORT: int = 13506
    REDIS_PASSWORD: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
