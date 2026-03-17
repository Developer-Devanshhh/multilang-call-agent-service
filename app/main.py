from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_mongodb, close_mongodb
from app.api import twilio, exotel, demo

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_mongodb()
    yield
    # Shutdown
    await close_mongodb()

app = FastAPI(
    title="JanVedha AI Voice Agent",
    description="Real-time Voice Complaint Registration Microservice",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for Demo HTML client
import os
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include Routers
app.include_router(twilio.router, prefix="/api")
app.include_router(exotel.router, prefix="/api")
app.include_router(demo.router, prefix="/api")

@app.get("/api/health")
async def health_check():
    return JSONResponse({
        "status": "ok",
        "service": "janvedha-voice-agent",
        "environment": settings.ENVIRONMENT,
        "telephony_provider": settings.TELEPHONY_PROVIDER
    })
