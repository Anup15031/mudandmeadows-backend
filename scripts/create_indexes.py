"""Create recommended MongoDB indexes for accommodations and bookings.
Run: python scripts/create_indexes.py
Requires `MONGODB_URL` and optional `DATABASE_NAME` env vars.
This creates a compound index to speed conflict checks for bookings.
"""
import os
import pymongo

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "resort_db")

if not MONGODB_URL:
	print("MONGODB_URL not set. Export it and re-run.")
	raise SystemExit(1)

client = pymongo.MongoClient(MONGODB_URL)
db = client[DATABASE_NAME]

print(f"Creating indexes on database '{DATABASE_NAME}'...")

# Compound index to speed overlap queries by accommodation and dates
db["bookings"].create_index([
	("accommodation_id", pymongo.ASCENDING),
	("check_in", pymongo.ASCENDING),
	("check_out", pymongo.ASCENDING),
], name="accom_checkin_checkout_idx")

# Per-night occupancy index to prevent double-booking at the granularity of a room-night
db["occupancies"].create_index([
	("accommodation_id", pymongo.ASCENDING),
	("date", pymongo.ASCENDING),
], name="accom_date_unique_idx", unique=True)

# Locks: ensure unique key and automatic expiry via TTL index on `expire_at`.
db["locks"].create_index([("key", pymongo.ASCENDING)], name="locks_key_unique", unique=True)
db["locks"].create_index([("expire_at", pymongo.ASCENDING)], name="locks_expire_ttl", expireAfterSeconds=0)

	# Ensure users and guests have indexes on email for fast lookup and uniqueness where appropriate
	try:
		db["users"].create_index([("email", pymongo.ASCENDING)], name="users_email_idx", unique=True)
	except Exception:
		# ignore if index exists or collection missing
		pass

	try:
		db["guests"].create_index([("email", pymongo.ASCENDING)], name="guests_email_idx")
	except Exception:
		pass

print("Indexes created.")
