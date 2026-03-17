"""
Database connection and initialization using Motor and Beanie.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.config import settings
from app.models.ticket import TicketMongo
from app.models.voice_call import VoiceCallLogMongo

# Global Motor client
client: AsyncIOMotorClient = None  # type: ignore

async def init_mongodb() -> None:
    """Initialize MongoDB connection and Beanie ODM."""
    global client
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    
    # Identify the database - fallback to 'civicai' if not in URI
    try:
        database = client.get_default_database()
    except Exception:
        database = client["civicai"]
    
    # Initialize Beanie with our document models
    await init_beanie(
        database=database,
        document_models=[
            TicketMongo,
            VoiceCallLogMongo
        ]
    )
    print(f"MongoDB ('{database.name}') and Beanie initialized successfully.")

async def close_mongodb() -> None:
    """Close MongoDB connection pool."""
    global client
    if client:
        client.close()
        print("MongoDB connection closed.")
