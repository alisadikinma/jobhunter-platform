import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.apify import router as apify_router
from app.api.applications import router as applications_router
from app.api.auth import router as auth_router
from app.api.callbacks import router as callbacks_router
from app.api.cv import router as cv_router
from app.api.emails import router as emails_router
from app.api.enrichment import router as enrichment_router
from app.api.firecrawl import router as firecrawl_router
from app.api.jobs import router as jobs_router
from app.api.mailbox import router as mailbox_router
from app.api.portfolio import router as portfolio_router
from app.api.scraper import router as scraper_router
from app.api.ws import router as ws_router
from app.scheduler import shutdown_scheduler, start_scheduler

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # JOBHUNTER_SCHEDULER_DISABLED=1 keeps the scheduler off in tests and
    # ad-hoc scripts. Default (unset / 0) starts it.
    if os.getenv("JOBHUNTER_SCHEDULER_DISABLED") in (None, "0", "false", "False"):
        scheduler = start_scheduler()
        _app.state.scheduler = scheduler
    else:
        _app.state.scheduler = None
        log.info("scheduler disabled via JOBHUNTER_SCHEDULER_DISABLED")

    try:
        yield
    finally:
        if _app.state.scheduler is not None:
            shutdown_scheduler(_app.state.scheduler)


app = FastAPI(title="JobHunter API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://jobs.alisadikinma.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(apify_router)
app.include_router(applications_router)
app.include_router(callbacks_router)
app.include_router(cv_router)
app.include_router(emails_router)
app.include_router(enrichment_router)
app.include_router(firecrawl_router)
app.include_router(jobs_router)
app.include_router(mailbox_router)
app.include_router(portfolio_router)
app.include_router(scraper_router)
app.include_router(ws_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/scheduler/status")
def scheduler_status():
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler is None:
        return {"running": False, "jobs": []}
    return {
        "running": scheduler.running,
        "jobs": [
            {
                "id": j.id,
                "name": j.name,
                "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None,
                "trigger": str(j.trigger),
            }
            for j in scheduler.get_jobs()
        ],
    }
