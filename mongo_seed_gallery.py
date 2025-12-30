"""Seed script to populate sample gallery images for local development."""
import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "resort_db")

SAMPLE_GALLERY = [
    {"imageUrl": "https://source.unsplash.com/featured/?resort,rooms", "caption": "Luxury Suite View", "category": "rooms", "isVisible": True, "createdAt": datetime.utcnow(), "updatedAt": datetime.utcnow()},
    {"imageUrl": "https://source.unsplash.com/featured/?resort,spa", "caption": "Ayurvedic Spa", "category": "spa", "isVisible": True, "createdAt": datetime.utcnow(), "updatedAt": datetime.utcnow()},
    {"imageUrl": "https://source.unsplash.com/featured/?resort,nature", "caption": "Nature Trail", "category": "nature", "isVisible": True, "createdAt": datetime.utcnow(), "updatedAt": datetime.utcnow()},
    {"imageUrl": "https://source.unsplash.com/featured/?resort,dining", "caption": "Dining Al Fresco", "category": "dining", "isVisible": True, "createdAt": datetime.utcnow(), "updatedAt": datetime.utcnow()},
    {"imageUrl": "https://source.unsplash.com/featured/?resort,activities", "caption": "Morning Yoga", "category": "activities", "isVisible": True, "createdAt": datetime.utcnow(), "updatedAt": datetime.utcnow()},
    {"imageUrl": "https://source.unsplash.com/featured/?resort,rooms", "caption": "Garden Suite", "category": "rooms", "isVisible": True, "createdAt": datetime.utcnow(), "updatedAt": datetime.utcnow()},
    {"imageUrl": "https://source.unsplash.com/featured/?resort,spa", "caption": "Treatment Room", "category": "spa", "isVisible": True, "createdAt": datetime.utcnow(), "updatedAt": datetime.utcnow()},
    {"imageUrl": "https://source.unsplash.com/featured/?resort,nature", "caption": "Sunset", "category": "nature", "isVisible": True, "createdAt": datetime.utcnow(), "updatedAt": datetime.utcnow()},
]


print("mongo_seed_gallery.py is neutralized. See scripts_disabled/mongo_seed_gallery.py for original script.")
