from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = "dev"

    DATABASE_URL: str = "postgresql://jobhunter:jobhunter@localhost:5433/jobhunter"
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    CLAUDE_PATH: str = "claude"
    CLAUDE_PLUGIN_PATH: str = "/app/claude-plugin"  # mount path inside API container
    CALLBACK_SECRET: str = ""  # shared token for Claude CLI -> FastAPI callbacks
    CALLBACK_API_URL: str = "http://localhost:8000"  # how the subprocess reaches us
    AGENT_JOB_LOG_DIR: str = "/tmp/jobhunter_agent_jobs"
    CV_STORAGE_DIR: str = "storage/cvs"  # rendered DOCX/PDF artifacts
    CV_REFERENCE_DOCX: str = ""  # optional Pandoc reference template path

    APIFY_FERNET_KEY: str = ""
    APIFY_LINKEDIN_ENABLED: bool = False
    APIFY_WELLFOUND_ACTOR: str = "bebity/wellfound-jobs-scraper"
    APIFY_LINKEDIN_ACTOR: str = "bebity/linkedin-jobs-scraper"

    # Custom-domain mailbox (Hostinger / Migadu / Fastmail / iCloud+ etc.).
    # Empty = mailer disabled; cold-email skill falls back to draft-only-in-DB.
    MAIL_SMTP_HOST: str = ""
    MAIL_SMTP_PORT: int = 465
    MAIL_IMAP_HOST: str = ""
    MAIL_IMAP_PORT: int = 993
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM_ADDRESS: str = ""
    MAIL_FROM_NAME: str = ""
    MAIL_DRAFTS_FOLDER: str = "Drafts"

    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""

    PROXY_URL: str = ""
    PROXY_USERNAME: str = ""
    PROXY_PASSWORD: str = ""

    FIRECRAWL_API_URL: str = "http://firecrawl-api:3002"
    FIRECRAWL_API_KEY: str = ""  # optional; self-hosted typically needs none
    FIRECRAWL_TIMEOUT_S: int = 60

    # Comma-separated list of directories scanned by the portfolio auditor.
    # Each subdir with a CLAUDE.md becomes a draft asset. Override via
    # env per-host (Linux VPS has no D:/ drive).
    PORTFOLIO_SCAN_PATHS: str = "~/.claude/plugins/cache"

    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "change-me"

    # extra="ignore" so the same .env can hold frontend (NEXT_PUBLIC_*) and
    # docker-compose (POSTGRES_PASSWORD) vars without crashing the API.
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @model_validator(mode="after")
    def _forbid_default_secrets_outside_dev(self):
        if self.APIFY_FERNET_KEY:
            from cryptography.fernet import Fernet

            try:
                Fernet(self.APIFY_FERNET_KEY.encode())
            except (ValueError, TypeError) as e:
                raise ValueError(f"APIFY_FERNET_KEY is not a valid Fernet key: {e}") from e

        if self.ENV == "dev":
            return self
        if self.JWT_SECRET == "change-me":
            raise ValueError("JWT_SECRET must be set to a real value when ENV != 'dev'")
        if len(self.JWT_SECRET.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET must be at least 32 bytes when ENV != 'dev' (RFC 7518 §3.2)")
        if self.ADMIN_PASSWORD == "change-me":
            raise ValueError("ADMIN_PASSWORD must be set to a real value when ENV != 'dev'")
        if self.CALLBACK_SECRET and len(self.CALLBACK_SECRET.encode("utf-8")) < 32:
            raise ValueError(
                "CALLBACK_SECRET must be at least 32 bytes when ENV != 'dev' "
                "(same threshold as JWT_SECRET)"
            )
        return self


settings = Settings()
