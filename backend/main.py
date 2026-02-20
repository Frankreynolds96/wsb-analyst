import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.api import router as api_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="WSB Stock Analyst",
    description="AI-powered stock analysis agent that monitors r/WallStreetBets",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    return {"status": "ok", "app": "WSB Stock Analyst"}
