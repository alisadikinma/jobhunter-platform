from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = "dev"

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

    @model_validator(mode="after")
    def _forbid_default_secrets_outside_dev(self):
        if self.ENV == "dev":
            return self
        if self.JWT_SECRET == "change-me":
            raise ValueError("JWT_SECRET must be set to a real value when ENV != 'dev'")
        if self.ADMIN_PASSWORD == "change-me":
            raise ValueError("ADMIN_PASSWORD must be set to a real value when ENV != 'dev'")
        return self


settings = Settings()
