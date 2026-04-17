from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.apify import router as apify_router
from app.api.auth import router as auth_router

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


@app.get("/health")
def health():
    return {"status": "ok"}
