from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Union
from bson import ObjectId
from datetime import datetime, timedelta
import pymongo
import asyncio
from uuid import uuid4
from fastapi import Depends
from resort_backend.routes.gallery import admin_key_dep
from resort_backend.lib.locks import acquire_lock, release_lock
from resort_backend.utils import get_db_or_503, serialize_doc
from resort_backend.routes.events import publish_event

router = APIRouter(prefix="/bookings", tags=["bookings"])

# Define a local BookingCreateRequest model for POST and BookingUpdateRequest for PUT
class BookingCreateRequest(BaseModel):
    guest_name: str
    guest_email: str
    guest_phone: str
    address: str
    city: str
    postal_code: str
    country: str
    accommodation_id: Union[str, List[str]]
    check_in: str
    check_out: str
    total_price: float
    payment_method: str = None
    guests: int = None
    adults: int = None
    children: int = None

class BookingUpdateRequest(BaseModel):
    guest_name: str = None
    guest_email: str = None
    guest_phone: str = None
    address: str = None
    city: str = None
    postal_code: str = None
    country: str = None
    accommodation_id: Union[str, List[str], None] = None
    check_in: str = None
    check_out: str = None
    total_price: float = None
    payment_method: str = None
    guests: int = None
    adults: int = None
    children: int = None


@router.get("/")
async def get_all_bookings(request: Request):
    """Get all bookings"""
    db = get_db_or_503(request)
    bookings = await db["bookings"].find().to_list(None)
    return [serialize_doc(b) for b in bookings]


@router.get("/{booking_id}")
async def get_booking(request: Request, booking_id: str):
    """Get a specific booking by ID"""
    db = get_db_or_503(request)
    try:
        # Try to fetch by _id (ObjectId) and fallback to string id field if needed
        try:
            obj_id = ObjectId(booking_id)
            booking = await db["bookings"].find_one({"_id": obj_id})
        except Exception:
            booking = None
        if not booking:
            # fallback: try by string id field (for legacy or non-ObjectId ids)
            booking = await db["bookings"].find_one({"id": booking_id})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking id")
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return serialize_doc(booking)


@router.get("/by-id")
async def get_booking_by_query(request: Request, booking_id: str):
    """Get a specific booking by ID (query param)"""
    db = get_db_or_503(request)
    booking = None
    if booking_id:
        try:
            obj_id = ObjectId(booking_id)
            booking = await db["bookings"].find_one({"_id": obj_id})
            if booking:
                return serialize_doc(booking)
        except Exception:
            pass
        # fallback: try as string id
        booking = await db["bookings"].find_one({"id": booking_id})
        if booking:
            return serialize_doc(booking)
    raise HTTPException(status_code=404, detail="Booking not found")


@router.post("/")
async def create_booking(request: Request, booking: BookingCreateRequest):
    db = get_db_or_503(request)
    booking_dict = booking.dict()
    booking_dict["created_at"] = datetime.utcnow()
    # Normalize accommodation_id to always be a list
    acc_ids = booking_dict["accommodation_id"]
    if isinstance(acc_ids, str):
        acc_ids = [acc_ids]
    booking_dict["accommodation_id"] = acc_ids

    # If request contains Authorization Bearer token, attach user id to booking
    try:
        from routes.auth import get_current_user
        user = None
        try:
            user = get_current_user(request)
        except Exception:
            user = None
        if user and user.get('id'):
            booking_dict['user_id'] = user.get('id')
    except Exception:
        # ignore if auth helper not available
        pass
    # Basic validation
    if booking_dict["check_in"] >= booking_dict["check_out"]:
        raise HTTPException(status_code=400, detail="check_in must be before check_out")

    # Capacity validation (if guest count provided). Accept `guests` or `adults`+`children`.
    try:
        if booking_dict.get("guests") is not None:
            guests_req = int(booking_dict.get("guests"))
        else:
            adults = int(booking_dict.get("adults") or 0)
            children = int(booking_dict.get("children") or 0)
            guests_req = (adults + children) if (adults + children) > 0 else None
    except Exception:
        guests_req = None
    if guests_req is not None:
        try:
            # try rooms collection first
            room = await db["rooms"].find_one({"_id": booking_dict.get("accommodation_id")})
            acc = None
            if not room:
                # try as ObjectId-like string or as accommodation doc
                try:
                    from bson import ObjectId as _OID
                    acc = await db["accommodations"].find_one({"_id": _OID(booking_dict.get("accommodation_id"))})
                except Exception:
                    acc = await db["accommodations"].find_one({"_id": booking_dict.get("accommodation_id")})

            # compute capacity
            total_cap = 0
            if room:
                total_cap = int(room.get("capacity") or room.get("sleeps") or 0)
                eb = room.get("extra_beds") if room.get("extra_beds") is not None else room.get("extra_bedding")
                extra_available = int(eb) if eb is not None else 0
            elif acc:
                total_cap = int(acc.get("capacity") or acc.get("sleeps") or 0)
                # if accommodation has rooms, sum their capacity
                try:
                    rooms = await db["rooms"].find({"$or": [{"accommodation_id": acc.get("_id")}, {"accommodation_id": str(acc.get("_id"))}]}).to_list(None)
                    if rooms:
                        total_cap = sum(int(r.get("capacity") or r.get("sleeps") or 0) for r in rooms)
                        extra_available = sum(int(r.get("extra_beds") or r.get("extra_bedding") or 0) for r in rooms)
                except Exception:
                    extra_available = 0
            else:
                extra_available = 0

            if booking_dict.get("allow_extra_beds"):
                requested_extra = int(booking_dict.get("extra_beds_qty") or 0)
                total_cap += min(extra_available, requested_extra)

            if guests_req > total_cap:
                raise HTTPException(status_code=400, detail=f"Selected accommodation does not accommodate {guests_req} guests; capacity is {total_cap}")
        except HTTPException:
            raise
        except Exception:
            # capacity check failure shouldn't block booking creation — proceed
            pass

    # Fix: Parse check_in and check_out from string to datetime
    try:
        check_in_dt = datetime.strptime(booking_dict["check_in"], "%Y-%m-%d")
        check_out_dt = datetime.strptime(booking_dict["check_out"], "%Y-%m-%d")
    except Exception:
        raise HTTPException(status_code=400, detail="check_in and check_out must be in YYYY-MM-DD format")

    if check_in_dt >= check_out_dt:
        raise HTTPException(status_code=400, detail="check_in must be before check_out")

    # Build list of nights (dates) the booking will occupy (check_in date .. check_out date - 1)
    start_date = check_in_dt
    end_date = check_out_dt
    nights = []
    d = start_date
    while d < end_date:
        nights.append(datetime(d.year, d.month, d.day))
        d += timedelta(days=1)

    client = getattr(request.app.state, "db_client", None)

    lock_owner = None
    lock_key = f"accom:{booking_dict['accommodation_id']}:{start_date.isoformat()}:{end_date.isoformat()}"

    # If we have a MongoDB client that supports transactions (replica set), prefer a transaction
    if client is not None and hasattr(client, "start_session"):
        try:
            async with client.start_session() as session:
                async with session.start_transaction():
                    result = await db["bookings"].insert_one(booking_dict, session=session)
                    booking_id = result.inserted_id
                    # create per-night occupancy documents to enforce uniqueness
                    occ_docs = []
                    for nd in nights:
                        occ_docs.append({
                            "accommodation_id": booking_dict["accommodation_id"],
                            "date": nd,
                            "booking_id": booking_id,
                            "created_at": datetime.utcnow(),
                        })
                    if occ_docs:
                        await db["occupancies"].insert_many(occ_docs, ordered=True, session=session)
                    created = await db["bookings"].find_one({"_id": booking_id}, session=session)
        except pymongo.errors.DuplicateKeyError:
            raise HTTPException(status_code=409, detail="Accommodation already booked for the selected dates")
        except pymongo.errors.PyMongoError:
            # If transactions aren't supported or another error occurred, fall back
            # to using a distributed lock, implemented below.
            created = None
        except Exception:
            created = None
    else:
        # No client/session available — fall back to using distributed lock
        created = None

    # If transactional path did not create the booking, attempt lock-based fallback
    if "created" not in locals() or created is None:
        # FIX: Remove unsupported retry_delay argument
        lock_owner = await acquire_lock(
            db,
            lock_key,
            owner=uuid4().hex,
            ttl_seconds=30,
            timeout=5.0
        )
        if not lock_owner:
            raise HTTPException(status_code=409, detail="Accommodation is busy; try again")
        try:
            overlap = await db["bookings"].find_one({
                "accommodation_id": booking_dict["accommodation_id"],
                "status": {"$ne": "cancelled"},
                "check_in": {"$lt": check_out_dt},
                "check_out": {"$gt": check_in_dt},
            })
            if overlap:
                raise HTTPException(status_code=409, detail="Accommodation already booked for the selected dates")
            # insert booking and create occupancy docs (best-effort)
            result = await db["bookings"].insert_one(booking_dict)
            booking_id = result.inserted_id
            occ_docs = []
            for nd in nights:
                occ_docs.append({
                    "accommodation_id": booking_dict["accommodation_id"],
                    "date": nd,
                    "booking_id": booking_id,
                    "created_at": datetime.utcnow(),
                })
            if occ_docs:
                try:
                    await db["occupancies"].insert_many(occ_docs, ordered=True)
                except Exception:
                    await db["bookings"].delete_one({"_id": booking_id})
                    raise HTTPException(status_code=409, detail="Accommodation already booked for the selected dates")
            created = await db["bookings"].find_one({"_id": booking_id})
        finally:
            try:
                await release_lock(db, lock_key, owner=lock_owner)
            except Exception:
                pass
    out = serialize_doc(created)
    # Notify subscribers that a booking was created
    try:
        publish_event({"event": "bookings.created", "booking_id": out.get("id"), "guest_email": out.get("guest_email")})
    except Exception:
        pass
    return out


@router.put("/{booking_id}")
async def update_booking(request: Request, booking_id: str, booking: BookingUpdateRequest):
    """Update a booking"""
    db = get_db_or_503(request)
    update_data = {k: v for k, v in booking.dict().items() if v is not None}
    # Normalize accommodation_id to always be a list if present
    if "accommodation_id" in update_data:
        acc_ids = update_data["accommodation_id"]
        if isinstance(acc_ids, str):
            acc_ids = [acc_ids]
        update_data["accommodation_id"] = acc_ids
    try:
        result = await db["bookings"].update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": update_data}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking id")
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    updated = await db["bookings"].find_one({"_id": ObjectId(booking_id)})
    return serialize_doc(updated)


@router.delete("/{booking_id}")
async def delete_booking(request: Request, booking_id: str):
    """Delete a booking"""
    db = get_db_or_503(request)
    try:
        b_id = ObjectId(booking_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking id")
    booking = await db["bookings"].find_one({"_id": b_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    # Remove occupancies associated with this booking (best-effort)
    try:
        await db["occupancies"].delete_many({"booking_id": b_id})
    except Exception:
        # booking deletion should proceed even if occupancy cleanup fails
        pass
    result = await db["bookings"].delete_one({"_id": b_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"message": "Booking deleted successfully"}


@router.get("/guest/{guest_email}")
async def get_guest_bookings(request: Request, guest_email: str):
    """Get all bookings for a specific guest"""
    db = get_db_or_503(request)
    bookings = await db["bookings"].find({"guest_email": guest_email}).to_list(None)
    return [serialize_doc(b) for b in bookings]


@router.get('/me')
async def my_bookings(request: Request):
    """Return bookings for the currently authenticated user (requires Authorization: Bearer <token>)"""
    # lightweight token auth reuse from auth.get_current_user
    from routes.auth import get_current_user
    user = get_current_user(request)
    db = get_db_or_503(request)
    # match by user id or user email
    q = {"$or": [{"user_id": user.get('id')}, {"guest_email": user.get('email')}]} if user else {}
    bookings = await db['bookings'].find(q).to_list(None)
    return [serialize_doc(b) for b in bookings]


@router.post("/{booking_id}/release", dependencies=[Depends(admin_key_dep)])
async def release_occupancies_endpoint(request: Request, booking_id: str):
    """Admin-safe endpoint: release occupancies associated with a booking id."""
    db = get_db_or_503(request)
    try:
        b_id = ObjectId(booking_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking id")
    res = await db["occupancies"].delete_many({"booking_id": b_id})
    return {"released": int(res.deleted_count)}


def get_db_or_503(request: Request):
    # Try to get db from request.app.state, fallback to raise 503 if not present
    db = getattr(request.app.state, "db", None)
    if db is None:
        # Try common alternatives for FastAPI MongoDB initialization
        db = getattr(request.app, "db", None)
    if db is None:
        db_client = getattr(request.app.state, "db_client", None)
        if db_client is not None:
            db = db_client.get_default_database() if hasattr(db_client, "get_default_database") else None
    if db is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db
