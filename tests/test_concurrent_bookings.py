import os
import asyncio
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from pymongo import MongoClient

from main import app


@pytest.mark.asyncio
async def test_concurrent_booking_attempts():
    mongo_url = os.getenv("MONGODB_URL")
    assert mongo_url is not None, "MONGODB_URL must be set to run this test"
    db_name = os.getenv("DATABASE_NAME", "resort_db")
    client = MongoClient(mongo_url)
    db = client[db_name]

    # Clear collections used by test
    db.bookings.delete_many({"accommodation_id": "test-room-concurrent"})
    db.occupancies.delete_many({"accommodation_id": "test-room-concurrent"})
    db.locks.delete_many({"key": {"$regex": "^accom:test-room-concurrent:"}})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Build booking payloads
        check_in = (datetime.utcnow() + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
        check_out = check_in + timedelta(days=2)

        payload = {
            "guest_name": "Concurrent Tester",
            "guest_email": "concurrent@example.com",
            "guest_phone": "123456",
            "accommodation_id": "test-room-concurrent",
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "total_price": 100.0,
        }

        async def try_book():
            r = await ac.post("/bookings/", json=payload)
            return r.status_code, r.json() if r.content else None

        # Launch several concurrent attempts
        tasks = [asyncio.create_task(try_book()) for _ in range(6)]
        results = await asyncio.gather(*tasks)

    client.close()

    successes = [r for r in results if r[0] == 200]
    conflicts = [r for r in results if r[0] == 409]

    # Exactly one should succeed; the rest should be conflicts
    assert len(successes) == 1, f"Expected 1 success, got {len(successes)}: {results}"
    assert len(conflicts) == 5, f"Expected 5 conflicts, got {len(conflicts)}"


@pytest.mark.asyncio
async def test_admin_release_allows_new_booking():
    mongo_url = os.getenv("MONGODB_URL")
    assert mongo_url is not None, "MONGODB_URL must be set to run this test"
    db_name = os.getenv("DATABASE_NAME", "resort_db")
    client = MongoClient(mongo_url)
    db = client[db_name]

    # Clean any previous artifacts
    db.bookings.delete_many({"accommodation_id": "test-room-release"})
    db.occupancies.delete_many({"accommodation_id": "test-room-release"})
    db.locks.delete_many({"key": {"$regex": "^accom:test-room-release:"}})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        check_in = (datetime.utcnow() + timedelta(days=3)).replace(hour=14, minute=0, second=0, microsecond=0)
        check_out = check_in + timedelta(days=2)

        payload = {
            "guest_name": "Release Tester",
            "guest_email": "release@example.com",
            "guest_phone": "123456",
            "accommodation_id": "test-room-release",
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "total_price": 150.0,
        }

        # Create a booking
        r = await ac.post("/bookings/", json=payload)
        assert r.status_code == 200
        booking = r.json()

        # Re-attempt booking concurrently should fail
        r2 = await ac.post("/bookings/", json=payload)
        assert r2.status_code == 409

        # Use admin release endpoint to free occupancy
        admin_key = os.getenv("ADMIN_API_KEY")
        headers = {}
        if admin_key:
            headers["X-Admin-Key"] = admin_key
        release_res = await ac.post(f"/bookings/{booking['id']}/release", headers=headers)
        assert release_res.status_code == 200

        # Now booking should succeed
        r3 = await ac.post("/bookings/", json=payload)
        assert r3.status_code == 200

    client.close()
