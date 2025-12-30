"""Migration script: backfill capacity_adults, capacity_children, extra_beds fields

Run with environment variables set:
  MONGODB_URL and DATABASE_NAME

Example:
  MONGODB_URL="..." DATABASE_NAME=adivasi python migrate_capacity_fields.py
"""
from pymongo import MongoClient
import os

MONGODB_URL = os.environ.get("MONGODB_URL")
if not MONGODB_URL:
    raise SystemExit("MONGODB_URL environment variable required")
DB = os.environ.get("DATABASE_NAME", "adivasi")

client = MongoClient(MONGODB_URL)
db = client[DB]

collections = ["rooms", "accommodations"]
count = 0
for coll in collections:
    for doc in db[coll].find({}):
        update = {}
        # Default adults capacity from `capacity` or `sleeps`
        if "capacity_adults" not in doc:
            base = doc.get("capacity") or doc.get("sleeps") or 1
            try:
                update["capacity_adults"] = int(base)
            except Exception:
                update["capacity_adults"] = 1
        if "capacity_children" not in doc:
            update.setdefault("capacity_children", 0)
        if "extra_beds_allowed" not in doc:
            update.setdefault("extra_beds_allowed", False)
        if "extra_beds_count" not in doc:
            eb = doc.get("extra_beds") if doc.get("extra_beds") is not None else doc.get("extra_bedding")
            try:
                update.setdefault("extra_beds_count", int(eb) if eb is not None else 0)
            except Exception:
                update.setdefault("extra_beds_count", 0)
        if "child_age_limit" not in doc:
            update.setdefault("child_age_limit", 12)
        if update:
            db[coll].update_one({"_id": doc["_id"]}, {"$set": update})
            count += 1

print(f"Migration completed. Updated {count} documents across {collections}.")
client.close()
