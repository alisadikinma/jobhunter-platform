from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.apify import router as apify_router
from app.api.applications import router as applications_router
from app.api.auth import router as auth_router
from app.api.callbacks import router as callbacks_router
from app.api.cv import router as cv_router
from app.api.enrichment import router as enrichment_router
from app.api.jobs import router as jobs_router
from app.api.portfolio import router as portfolio_router
from app.api.scraper import router as scraper_router

app = FastAPI(title="JobHunter API", version="0.1.0")

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
app.include_router(enrichment_router)
app.include_router(jobs_router)
app.include_router(portfolio_router)
app.include_router(scraper_router)


@app.get("/health")
def health():
    return {"status": "ok"}
