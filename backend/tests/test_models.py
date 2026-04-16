def test_all_models_importable():
    from app.models.user import User
    from app.models.company import Company
    from app.models.job import ScrapedJob
    from app.models.application import Application, ApplicationActivity
    from app.models.cv import MasterCV, GeneratedCV, CoverLetter
    from app.models.email_draft import EmailDraft
    from app.models.scrape_config import ScrapeConfig
    from app.models.agent_job import AgentJob
    from app.models.apify_account import ApifyAccount, ApifyUsageLog
    from app.models.portfolio_asset import PortfolioAsset

    assert User.__tablename__ == "users"
    assert Company.__tablename__ == "companies"
    assert ScrapedJob.__tablename__ == "scraped_jobs"
    assert Application.__tablename__ == "applications"
    assert ApplicationActivity.__tablename__ == "application_activities"
    assert MasterCV.__tablename__ == "master_cv"
    assert GeneratedCV.__tablename__ == "generated_cvs"
    assert CoverLetter.__tablename__ == "cover_letters"
    assert EmailDraft.__tablename__ == "email_drafts"
    assert ScrapeConfig.__tablename__ == "scrape_configs"
    assert AgentJob.__tablename__ == "agent_jobs"
    assert ApifyAccount.__tablename__ == "apify_accounts"
    assert ApifyUsageLog.__tablename__ == "apify_usage_log"
    assert PortfolioAsset.__tablename__ == "portfolio_assets"
