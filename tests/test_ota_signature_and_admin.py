import os
import json
import hmac
import hashlib
import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from pymongo import MongoClient
from datetime import datetime, timedelta


def make_signature(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_yatra_sample_webhook_and_admin(monkeypatch):
    sample_path = os.getenv("SAMPLE_YATRA_PAYLOAD")
    secret = os.getenv("YATRA_WEBHOOK_SECRET")
    if not sample_path or not secret:
        pytest.skip("Provide SAMPLE_YATRA_PAYLOAD and YATRA_WEBHOOK_SECRET to run this test")

    with open(sample_path, "rb") as f:
        body = f.read()

    sig = make_signature(secret, body)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Content-Type": "application/json", "X-Yatra-Signature": sig}
        r = await ac.post("/ota/webhook", content=body, headers=headers)
        assert r.status_code in (200, 409)

        # If admin key provided, call locks endpoint
        admin_key = os.getenv("ADMIN_API_KEY")
        if admin_key:
            headers2 = {"X-Admin-Key": admin_key}
            r2 = await ac.get("/ota/locks", headers=headers2)
            assert r2.status_code == 200

