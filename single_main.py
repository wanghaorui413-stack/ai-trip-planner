import logging
import logging.config
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from logging_config import setup_logging
from api_routes import router as api_router


setup_logging()
logger = logging.getLogger(__name__)


# --- FastAPI App Initialization ---
app = FastAPI(
    title="AI Trip Planner Backend",
    version="1.0.0",
)

# --- Lifespan Events Logging ---
# Log when the application starts and stops
@app.on_event("startup")
async def on_startup():
    logger.info("FastAPI application is starting up...")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("FastAPI application is shutting down...")


# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def read_health():
    """
    A simple endpoint that returns a 200 OK status if the API is running.
    """
    logger.info("Health check endpoint was accessed.")
    return {"status": "ok"}


app.include_router(api_router, prefix="/api")
logger.info("API router included with prefix /api.")


if __name__ == "__main__":
    logger.info("Starting Uvicorn server directly for local development.")
    uvicorn.run(app, host="0.0.0.0", port=8000)

