"""APScheduler integration — in-process, no broker needed.

Loads active scrape_configs at startup and registers one cron job per
config. On fire, the job re-uses scraper_service.run_scrape_config against
a short-lived session.

Exposed via FastAPI lifespan (main.py) so shutdown is clean.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.models.scrape_config import ScrapeConfig
from app.services.scraper_service import run_scrape_config

log = logging.getLogger(__name__)


_MISFIRE_GRACE_S = 300
_SCRAPE_JOB_PREFIX = "scrape-config-"


def _run_config_job(config_id: int) -> None:
    """Callable fired by APScheduler. Runs in a worker thread."""
    db = SessionLocal()
    try:
        config = db.get(ScrapeConfig, config_id)
        if config is None or not config.is_active:
            log.info("skipping scrape run: config %s missing or inactive", config_id)
            return
        result = run_scrape_config(db, config)
        log.info(
            "scraped config %s: new=%d duplicates=%d",
            config_id, result.new_jobs, result.duplicates,
        )
    except Exception:
        log.exception("scrape job failed for config %s", config_id)
        db.rollback()
    finally:
        db.close()


def build_scheduler() -> BackgroundScheduler:
    return BackgroundScheduler(
        timezone="UTC",
        job_defaults={
            "coalesce": True,  # collapse missed runs into one
            "max_instances": 1,  # never overlap a config with itself
            "misfire_grace_time": _MISFIRE_GRACE_S,
        },
    )


def register_scrape_configs(scheduler: BackgroundScheduler) -> int:
    """Install one cron trigger per active scrape_config. Returns count."""
    db = SessionLocal()
    try:
        configs = db.query(ScrapeConfig).filter(ScrapeConfig.is_active.is_(True)).all()
        registered = 0
        for cfg in configs:
            job_id = f"{_SCRAPE_JOB_PREFIX}{cfg.id}"
            try:
                trigger = CronTrigger.from_crontab(
                    cfg.cron_expression or "0 */3 * * *",
                    timezone="UTC",
                )
            except ValueError as e:
                log.warning("invalid cron %r on config %s: %s", cfg.cron_expression, cfg.id, e)
                continue

            scheduler.add_job(
                _run_config_job,
                trigger=trigger,
                id=job_id,
                name=f"scrape: {cfg.name}",
                args=[int(cfg.id)],
                replace_existing=True,
            )
            registered += 1
        return registered
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    """Start the scheduler and register all active scrape configs."""
    scheduler = build_scheduler()
    registered = register_scrape_configs(scheduler)
    scheduler.start()
    log.info("scheduler started with %d scrape job(s)", registered)
    return scheduler


def shutdown_scheduler(scheduler: BackgroundScheduler) -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("scheduler shut down")
