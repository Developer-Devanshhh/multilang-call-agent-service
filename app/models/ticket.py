"""
MongoDB Document: Ticket
Mirrors the core domain object in JanVedha-AI
"""
from beanie import Document, Indexed
from pydantic import Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.enums import TicketSource, TicketStatus, PriorityLabel

class TicketMongo(Document):
    ticket_code: Indexed(str, unique=True)          # type: ignore
    source: TicketSource = TicketSource.VOICE_CALL
    source_url: Optional[str] = None
    description: str
    dept_id: Indexed(str)                            # type: ignore
    issue_category: Optional[str] = None             
    ward_id: Optional[Indexed(int)] = None           # type: ignore
    zone_id: Optional[int] = None

    location: Optional[Dict[str, Any]] = None
    coordinates: Optional[str] = None
    location_text: Optional[str] = None

    photo_url: Optional[str] = None
    before_photo_url: Optional[str] = None
    after_photo_url: Optional[str] = None

    reporter_phone: Optional[str] = Field(None, max_length=15)
    reporter_name: Optional[str] = Field(None, max_length=100)
    reporter_user_id: Optional[str] = None          

    consent_given: bool = False
    consent_timestamp: Optional[datetime] = None

    language_detected: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_routing_reason: Optional[str] = None
    ai_suggestions: Optional[List[str]] = None       

    priority_score: float = 0.0
    priority_label: Optional[PriorityLabel] = None
    priority_source: str = "rules"                   

    status: TicketStatus = TicketStatus.OPEN
    report_count: int = 1
    requires_human_review: bool = False
    is_validated: bool = False

    estimated_cost: Optional[float] = None
    citizen_satisfaction: Optional[int] = None

    sla_deadline: Optional[datetime] = None
    completion_deadline: Optional[datetime] = None
    completion_deadline_confirmed_by: Optional[str] = None  

    social_media_mentions: int = 0

    assigned_officer_id: Optional[str] = None       
    assigned_at: Optional[datetime] = None
    technician_id: Optional[str] = None              

    seasonal_alert: Optional[str] = None             
    scheduled_date: Optional[datetime] = None        
    ai_suggested_date: Optional[datetime] = None     

    status_timeline: List[Dict[str, Any]] = Field(default_factory=list)
    remarks: List[Dict[str, Any]] = Field(default_factory=list)
    blockchain_hash: Optional[str] = Field(None, max_length=66)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

    work_verified: Optional[bool] = None          
    work_verification_confidence: Optional[float] = None  
    work_verification_method: Optional[str] = None  
    work_verification_explanation: Optional[str] = None  
    work_verified_at: Optional[datetime] = None

    class Settings:
        name = "tickets"
        indexes = [
            "status",
            "priority_label",
            "dept_id",
            "ward_id",
            "created_at",
            [("location", "2dsphere")],
        ]

    class Config:
        populate_by_name = True
