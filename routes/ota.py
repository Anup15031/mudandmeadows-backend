from fastapi import APIRouter, Request, HTTPException, Depends
from datetime import datetime, timedelta
from resort_backend.lib.locks import acquire_lock, release_lock
from bson import ObjectId
from resort_backend.utils import get_db_or_503, serialize_doc
import pymongo
import os
from lib import ota_adapters
from resort_backend.lib.webhooks import verify_hmac_sha256
from resort_backend.routes.gallery import admin_key_dep

router = APIRouter(tags=["ota"])


@router.post("/webhook")
async def ota_webhook(request: Request):
    """Generic OTA webhook receiver.

    Expected JSON shape (generic):
    {
      "source": "yatra" | "mmt" | "booking_yatra",
      "external_id": "...",
      "guest_name": "...",
      "guest_email": "...",
      "guest_phone": "...",
      "accommodation_id": "...",
      "check_in": "ISO8601",
      "check_out": "ISO8601",
      "total_price": 123.45,
      "status": "confirmed" | "cancelled" | "modified"
    }

    Adapter mapping functions can be added in `lib/ota_adapters.py`.
    """
    db = get_db_or_503(request)
    body_bytes = await request.body()
    payload = await request.json()
    source = payload.get("source")
    external_id = payload.get("external_id")
    if not source or not external_id:
        raise HTTPException(status_code=400, detail="source and external_id required")

    # Verify signature if provider secret is configured
    cfg = ota_adapters.get_provider_config(source)
    secret = cfg.get("secret")
    sig_header = cfg.get("signature_header") or "X-Signature"
    header_val = request.headers.get(sig_header)
    if secret:
        ok = verify_hmac_sha256(header_val, body_bytes, secret)
        if not ok:
            raise HTTPException(status_code=403, detail="Invalid webhook signature")

    # Allow provider-specific mapping via adapters
    mapped = None
    lower_source = source.lower()
    if "yatra" in lower_source:
        mapped = ota_adapters.map_yatra(payload)
    elif "mmt" in lower_source or "makemytrip" in lower_source:
        mapped = ota_adapters.map_mmt(payload)
    else:
        # Fallback: assume generic shape
        mapped = {
            "source": source,
            "external_id": external_id,
            "guest_name": payload.get("guest_name"),
            "guest_email": payload.get("guest_email"),
            "guest_phone": payload.get("guest_phone"),
            "accommodation_id": payload.get("accommodation_id"),
            "check_in": payload.get("check_in"),
            "check_out": payload.get("check_out"),
            "total_price": payload.get("total_price", 0),
            "status": payload.get("status", "confirmed"),
        }

    guest_name = mapped.get("guest_name")
    guest_email = mapped.get("guest_email")
    guest_phone = mapped.get("guest_phone")
    accommodation_id = mapped.get("accommodation_id")
    check_in = mapped.get("check_in")
    check_out = mapped.get("check_out")
    total_price = mapped.get("total_price", 0)
    status = mapped.get("status", "confirmed")

    try:
        ci = datetime.fromisoformat(check_in)
        co = datetime.fromisoformat(check_out)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid check_in/check_out format")

    # Idempotency: check if we already mapped this external booking
    existing = await db["ota_bookings"].find_one({"source": source, "external_id": external_id})
    client = getattr(request.app.state, "db_client", None)

    # If OTA reports cancellation, attempt to cancel internal booking and free occupancies
    if existing and status == "cancelled":
        try:
            b_id = existing.get("booking_id")
            if b_id:
                await db["occupancies"].delete_many({"booking_id": b_id})
                await db["bookings"].update_one({"_id": b_id}, {"$set": {"status": "cancelled"}})
            await db["ota_bookings"].update_one({"_id": existing["_id"]}, {"$set": {"status": "cancelled"}})
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to cancel booking")
        return {"status": "cancelled"}

    # Create or update mapping
    booking_doc = {
        "guest_name": guest_name or "",
        "guest_email": guest_email or "",
        "guest_phone": guest_phone or "",
        "accommodation_id": accommodation_id,
        "check_in": ci,
        "check_out": co,
        "total_price": total_price,
        "status": "confirmed" if status != "cancelled" else "cancelled",
        "created_at": datetime.utcnow(),
    }

    # Try transactional path first
    if existing is None:
        # create new mapping + booking
        lock_key = f"accom:{accommodation_id}:{ci.date().isoformat()}:{co.date().isoformat()}"
        lock_owner = None
        # prefer transactions when available
        if client is not None and hasattr(client, "start_session"):
            try:
                async with client.start_session() as session:
                    async with session.start_transaction():
                        res = await db["bookings"].insert_one(booking_doc, session=session)
                        booking_id = res.inserted_id
                        # per-night occupancies
                        occs = []
                        d = ci.date()
                        while d < co.date():
                            occs.append({"accommodation_id": accommodation_id, "date": datetime(d.year, d.month, d.day), "booking_id": booking_id, "created_at": datetime.utcnow()})
                            d = d + timedelta(days=1)
                        if occs:
                            await db["occupancies"].insert_many(occs, ordered=True, session=session)
                        await db["ota_bookings"].insert_one({"source": source, "external_id": external_id, "booking_id": booking_id, "status": booking_doc["status"], "created_at": datetime.utcnow()}, session=session)
                        created = await db["bookings"].find_one({"_id": booking_id}, session=session)
                        return serialize_doc(created)
            except pymongo.errors.DuplicateKeyError:
                raise HTTPException(status_code=409, detail="Accommodation already booked for the selected dates")
            except Exception:
                # fall through to lock-based fallback
                pass

        # lock-based fallback when transactions not possible
        lock_owner = await acquire_lock(db, lock_key, ttl_seconds=30, timeout=5.0)
        if not lock_owner:
            raise HTTPException(status_code=409, detail="Accommodation busy; try again")
        try:
            # re-check overlap
            overlap = await db["bookings"].find_one({"accommodation_id": accommodation_id, "status": {"$ne": "cancelled"}, "check_in": {"$lt": co}, "check_out": {"$gt": ci}})
            if overlap:
                raise HTTPException(status_code=409, detail="Accommodation already booked for the selected dates")
            res = await db["bookings"].insert_one(booking_doc)
            booking_id = res.inserted_id
            occs = []
            d = ci.date()
            while d < co.date():
                occs.append({"accommodation_id": accommodation_id, "date": datetime(d.year, d.month, d.day), "booking_id": booking_id, "created_at": datetime.utcnow()})
                d = d + timedelta(days=1)
            if occs:
                try:
                    await db["occupancies"].insert_many(occs, ordered=True)
                except pymongo.errors.DuplicateKeyError:
                    await db["bookings"].delete_one({"_id": booking_id})
                    raise HTTPException(status_code=409, detail="Accommodation already booked for the selected dates")
            await db["ota_bookings"].insert_one({"source": source, "external_id": external_id, "booking_id": booking_id, "status": booking_doc["status"], "created_at": datetime.utcnow()})
            created = await db["bookings"].find_one({"_id": booking_id})
            return serialize_doc(created)
        finally:
            try:
                await release_lock(db, lock_key, owner=lock_owner)
            except Exception:
                pass
    else:
        # Update path: map incoming changes to internal booking
        b_id = existing.get("booking_id")
        if not b_id:
            raise HTTPException(status_code=500, detail="Mapped booking not found")
        # For simplicity, support modified -> update dates/price and cancelled handled earlier
        try:
            await db["bookings"].update_one({"_id": b_id}, {"$set": {"check_in": ci, "check_out": co, "total_price": total_price, "guest_name": guest_name, "guest_email": guest_email}})
            await db["ota_bookings"].update_one({"_id": existing["_id"]}, {"$set": {"updated_at": datetime.utcnow(), "status": status}})
            updated = await db["bookings"].find_one({"_id": b_id})
            return serialize_doc(updated)
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to update mapped booking")


@router.get("/locks", dependencies=[Depends(admin_key_dep)])
async def get_locks_and_mappings(request: Request, limit: int = 100):
    """Admin endpoint: inspect current locks and OTA mappings."""
    db = get_db_or_503(request)
    locks = await db["locks"].find().sort("created_at", -1).to_list(length=limit)
    mappings = await db["ota_bookings"].find().sort("created_at", -1).limit(limit).to_list(length=limit)
    return {"locks": [serialize_doc(l) for l in locks], "mappings": [serialize_doc(m) for m in mappings]}
