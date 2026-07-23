"""FastAPI entry point with planning and authenticated persistence routes."""

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_routes import router as planning_router
from auth_api_routes import router as auth_router
from auth_store import init_database
from logging_config import setup_logging


setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Trip Planner Backend", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    init_database()
    logger.info("Authenticated trip planner API is starting.")


@app.get("/health")
def read_health():
    return {"status": "ok"}


app.include_router(auth_router, prefix="/api")
app.include_router(planning_router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
