import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"

    # Databases
    MONGODB_URI: str = "mongodb://localhost:27017/civicai"

    # API Keys
    SARVAM_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Twilio Configuration
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Google Cloud Fallbacks
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # Voice Agent Settings
    TELEPHONY_PROVIDER: str = "demo" # demo | twilio | exotel
    SARVAM_STT_MODEL: str = "saaras:v3"
    SARVAM_TTS_MODEL: str = "bulbul:v1"
    SARVAM_TRANSLATE_MODEL: str = "mayura:v1"
    
    # Thresholds & Timeouts
    SARVAM_CONFIDENCE_THRESHOLD: float = 0.70
    VOICE_SILENCE_TIMEOUT_MS: int = 1500
    VOICE_SESSION_TTL_SECONDS: int = 600
    VOICE_MAX_CALL_DURATION_SECONDS: int = 300

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
