"""Seed script to populate a sample site config for local development."""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "resort_db")

SAMPLE_SITE_CONFIG = {
    "siteName": "Resort",
    "apiBase": "/api",
    "theme": "default",
    "contactEmail": "info@resort.com",
    "createdAt": None,
    "updatedAt": None
}

if __name__ == "__main__":
    from datetime import datetime
    SAMPLE_SITE_CONFIG["createdAt"] = datetime.utcnow()
    SAMPLE_SITE_CONFIG["updatedAt"] = datetime.utcnow()
    client = MongoClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    result = db["site"].replace_one({}, SAMPLE_SITE_CONFIG, upsert=True)
    print(f"Seeded site config: {result.upserted_id or 'updated existing'}")
    client.close()
