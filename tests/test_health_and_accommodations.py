import os
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
        assert r.json().get("status") == "healthy"


@pytest.mark.asyncio
async def test_accommodations_db_unavailable(monkeypatch):
    # simulate DB not initialized by clearing app.state.db
    transport = ASGITransport(app=app)
    # ensure state exists and db is None
    app.state.db = None
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/accommodations/")
        assert r.status_code == 503
