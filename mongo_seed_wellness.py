"""Seed script to populate sample wellness services for local development."""
import motor.motor_asyncio
import asyncio
from datetime import datetime

MONGODB_URL = "mongodb://localhost:27017"
DB_NAME = "resort"
COLLECTION = "wellness"

# Sample wellness data (selecting best from provided images)
WELLNESS_SERVICES = [
    {
        "name": "Ayurveda",
        "description": "Traditional Indian healing therapies for holistic wellness and rejuvenation.",
        "price": 120.0,
        "duration_minutes": 90,
        "benefits": ["Detoxification", "Stress Relief", "Immunity Boost"],
        "images": ["/images/wellness/ayurveda.jpg"],
        "rating": 4.9,
        "created_at": datetime.utcnow(),
    },
    {
        "name": "Yoga & Meditation",
        "description": "Guided yoga and meditation sessions for mind-body harmony and inner peace.",
        "price": 80.0,
        "duration_minutes": 60,
        "benefits": ["Flexibility", "Mental Clarity", "Emotional Balance"],
        "images": ["/images/wellness/yoga-meditation.jpg"],
        "rating": 4.8,
        "created_at": datetime.utcnow(),
    },
    {
        "name": "Spa Therapies",
        "description": "Luxurious spa treatments blending ancient and modern techniques for relaxation.",
        "price": 150.0,
        "duration_minutes": 75,
        "benefits": ["Relaxation", "Skin Glow", "Muscle Relief"],
        "images": ["/images/wellness/spa-therapies.jpg"],
        "rating": 4.7,
        "created_at": datetime.utcnow(),
    },
    {
        "name": "Detox Programs",
        "description": "Comprehensive detoxification programs to cleanse and revitalize your body.",
        "price": 200.0,
        "duration_minutes": 120,
        "benefits": ["Body Cleanse", "Energy Boost", "Weight Management"],
        "images": ["/images/wellness/detox-programs.jpg"],
        "rating": 4.8,
        "created_at": datetime.utcnow(),
    },
    {
        "name": "Sound Healing",
        "description": "Therapeutic sound sessions using ancient instruments for deep relaxation.",
        "price": 90.0,
        "duration_minutes": 60,
        "benefits": ["Deep Relaxation", "Mental Clarity", "Emotional Healing"],
        "images": ["/images/wellness/sound-healing.jpg"],
        "rating": 4.9,
        "created_at": datetime.utcnow(),
    },
    {
        "name": "Holistic Detox",
        "description": "A blend of yogic and ayurvedic detox practices for total body renewal.",
        "price": 180.0,
        "duration_minutes": 100,
        "benefits": ["Holistic Cleanse", "Vitality", "Immunity"],
        "images": ["/images/wellness/holistic-detox.jpg"],
        "rating": 4.8,
        "created_at": datetime.utcnow(),
    },
    {
        "name": "Stress Management",
        "description": "Personalized therapies to reduce stress and restore balance.",
        "price": 110.0,
        "duration_minutes": 70,
        "benefits": ["Calmness", "Focus", "Resilience"],
        "images": ["/images/wellness/stress-management.jpg"],
        "rating": 4.7,
        "created_at": datetime.utcnow(),
    },
    {
        "name": "Ayurvedic Rejuvenation & Immunity Booster",
        "description": "Signature ayurvedic therapies to rejuvenate and strengthen immunity.",
        "price": 210.0,
        "duration_minutes": 120,
        "benefits": ["Rejuvenation", "Immunity", "Longevity"],
        "images": ["/images/wellness/ayurvedic-rejuvenation.jpg"],
        "rating": 4.9,
        "created_at": datetime.utcnow(),
    },
]

async def seed_wellness():
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    await db[COLLECTION].delete_many({})  # Clear existing
    await db[COLLECTION].insert_many(WELLNESS_SERVICES)
    print(f"Seeded {len(WELLNESS_SERVICES)} wellness services.")

if __name__ == "__main__":
    asyncio.run(seed_wellness())
