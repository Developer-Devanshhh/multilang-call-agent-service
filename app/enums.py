from enum import Enum

class TicketSource(str, Enum):
    WEB_PORTAL = "web_portal"
    MOBILE_APP = "mobile_app"
    VOICE_CALL = "voice_call"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    TWITTER = "twitter"

class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"

class PriorityLabel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
