import os
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from pymongo import MongoClient

import sys
import os
# Ensure resort_backend package path is importable when running pytest from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app


@pytest.mark.asyncio
async def test_over_capacity_booking_rejected():
    mongo_url = os.getenv("MONGODB_URL")
    assert mongo_url is not None, "MONGODB_URL must be set to run this test"
    db_name = os.getenv("DATABASE_NAME", "resort_db")
    client = MongoClient(mongo_url)
    db = client[db_name]

    # Seed a single room/accommodation with small capacity
    db.rooms.delete_many({"accommodation_id": "cap-test-room"})
    db.accommodations.delete_many({"_id": "cap-test-room"})
    room_doc = {"_id": "cap-test-room", "capacity": 2, "price_per_night": 100, "available": True}
    db.rooms.replace_one({"_id": room_doc["_id"]}, room_doc, upsert=True)

    # Ensure app has DB attached when using ASGITransport (lifespan may not run in some test harnesses)
    from database import connect_db, get_db
    await connect_db()
    app.state.db = get_db()
    app.state.db_client = getattr(__import__("database"), "client", None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        check_in = (datetime.utcnow() + timedelta(days=5)).replace(hour=14, minute=0, second=0, microsecond=0)
        check_out = check_in + timedelta(days=2)
        payload = {
            "guest_name": "Capacity Tester",
            "guest_email": "cap@example.com",
            "guest_phone": "123456",
            "accommodation_id": "cap-test-room",
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "total_price": 200.0,
            "guests": 9,
            "allow_extra_beds": False,
            "extra_beds_qty": 0,
        }
        r = await ac.post("/bookings/", json=payload)
        assert r.status_code == 400

    client.close()
