from beanie import Document, Indexed
from pydantic import Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class VoiceCallLogMongo(Document):
    """
    Records every incoming voice call and its AI interaction lifecycle.
    Collection: voice_calls
    """
    call_id: Indexed(str, unique=True) # type: ignore
    provider: str                      # twilio | exotel | demo
    caller_phone: str
    language_detected: Optional[str] = None
    
    transcript_raw: str = ""
    transcript_english: str = ""
    
    conversation_log: List[Dict[str, Any]] = Field(default_factory=list) 
    # Example: [{"role": "user", "text": "...", "timestamp": "..."}, ...]
    
    extracted_data: Optional[Dict[str, Any]] = None
    
    ticket_code: Optional[str] = None  # Link to the generated TicketMongo
    
    status: str = "in_progress"        # in_progress | completed | abandoned | error
    duration_seconds: float = 0.0
    
    stt_provider_used: str = "sarvam"  # or 'google' (fallback)
    tts_provider_used: str = "sarvam"
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

    class Settings:
        name = "voice_calls"
        indexes = [
            "caller_phone",
            "status",
            "created_at",
            "ticket_code"
        ]
