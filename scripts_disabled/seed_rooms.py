"""Seed per-accommodation room documents for local development.
Moved from `scripts/seed_rooms.py` to `scripts_disabled/` to avoid accidental seeding.
Run manually only if you intentionally want to create demo room docs.
"""
import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "resort_db")

if not MONGODB_URL:
    print("MONGODB_URL not set; aborting seed")
    raise SystemExit(1)

client = MongoClient(MONGODB_URL)
db = client[DATABASE_NAME]

accommodations = list(db.accommodations.find({}, {"_id": 1, "name": 1, "price_per_night": 1, "capacity": 1}))
if not accommodations:
    print("No accommodations found; make sure you've seeded accommodations first (run mongo_seed.py)")
    raise SystemExit(0)

created = 0
skipped = 0
for acc in accommodations:
    acc_id = acc.get("_id")
    acc_name = acc.get("name") or str(acc_id)
    has_rooms_count = db.rooms.count_documents({"$or": [{"accommodation_id": acc_id}, {"accommodation_id": str(acc_id)}]})
    if has_rooms_count > 0:
        print(f"Skipping {acc_name} ({acc_id}) — already has {has_rooms_count} room(s)")
        skipped += 1
        continue

    # Create 2 rooms by default; capacity/readable defaults
    num_rooms = 2
    base_price = acc.get("price_per_night") or 0
    cap = acc.get("capacity") or 2
    docs = []
    for i in range(1, num_rooms + 1):
        doc = {
            "accommodation_id": str(acc_id),
            "name": f"{acc_name} Room {i}",
            "capacity": max(1, min(cap, 4)),
            "price_per_night": base_price,
            "available": True,
            "created_at": datetime.utcnow()
        }
        docs.append(doc)

    res = db.rooms.insert_many(docs)
    print(f"Inserted {len(res.inserted_ids)} room(s) for {acc_name} ({acc_id})")
    created += len(res.inserted_ids)

print(f"Done. Created {created} rooms, skipped {skipped} accommodations.")
