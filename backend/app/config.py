from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://jobhunter:jobhunter@localhost:5433/jobhunter"
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    CLAUDE_PATH: str = "claude"

    APIFY_FERNET_KEY: str = ""
    APIFY_LINKEDIN_ENABLED: bool = False

    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""

    PROXY_URL: str = ""
    PROXY_USERNAME: str = ""
    PROXY_PASSWORD: str = ""

    FIRECRAWL_API_URL: str = "http://firecrawl-api:3002"

    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "change-me"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
