import os
import asyncio
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from pymongo import MongoClient

from main import app


@pytest.mark.asyncio
async def test_fallback_lock_path(monkeypatch):
    """Force the fallback path by removing app.state.db_client and ensure bookings still serialize to single success."""
    mongo_url = os.getenv("MONGODB_URL")
    assert mongo_url is not None, "MONGODB_URL must be set to run this test"
    db_name = os.getenv("DATABASE_NAME", "resort_db")
    client = MongoClient(mongo_url)
    db = client[db_name]

    # Clean test artifacts
    db.bookings.delete_many({"accommodation_id": "test-fallback-room"})
    db.occupancies.delete_many({"accommodation_id": "test-fallback-room"})
    db.locks.delete_many({"key": {"$regex": "^accom:test-fallback-room:"}})

    # Force fallback by removing db_client so transaction path is not taken
    monkeypatch.setattr(app.state, "db_client", None, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        check_in = (datetime.utcnow() + timedelta(days=4)).replace(hour=14, minute=0, second=0, microsecond=0)
        check_out = check_in + timedelta(days=2)
        payload = {
            "guest_name": "Fallback Tester",
            "guest_email": "fallback@example.com",
            "guest_phone": "000",
            "accommodation_id": "test-fallback-room",
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "total_price": 200.0,
        }

        async def try_book():
            r = await ac.post("/bookings/", json=payload)
            return r.status_code

        tasks = [asyncio.create_task(try_book()) for _ in range(4)]
        results = await asyncio.gather(*tasks)

    client.close()

    successes = [s for s in results if s == 200]
    conflicts = [s for s in results if s == 409]
    assert len(successes) == 1
    assert len(conflicts) == 3
