import motor.motor_asyncio
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("resort_backend.database")

# Read config from environment (no hard-coded credentials)
# Read env inside connect_db to pick up runtime env changes
DATABASE_NAME = os.getenv("DATABASE_NAME", "resort_db")

client = None
db = None

async def connect_db():
    """Initialize MongoDB client and database handle using env vars."""
    global client, db
    MONGODB_URL = os.getenv("MONGODB_URL")
    if not MONGODB_URL:
        logger.error("MONGODB_URL not set; database will not be initialized")
        client = None
        db = None
        return
    try:
        # Use a reasonable serverSelectionTimeout to fail fast in dev
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
        # verify connection with a ping (awaitable)
        try:
            await client.admin.command("ping")
        except Exception:
            logger.exception("MongoDB ping failed after client creation")
            client.close()
            client = None
            db = None
            return
        db = client[DATABASE_NAME]
        logger.info("Connected to MongoDB database=%s", DATABASE_NAME)
    except Exception:
        logger.exception("Failed to connect to MongoDB")
        client = None
        db = None

async def close_db():
    """Close MongoDB connection if open."""
    global client
    if client:
        try:
            client.close()
            logger.info("Disconnected from MongoDB")
        except Exception:
            logger.exception("Error while closing MongoDB connection")

def get_db():
    """Synchronous getter for the db handle (may be None)."""
    return db
