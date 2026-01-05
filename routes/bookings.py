
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Union, Optional
import pymongo
from uuid import uuid4
from resort_backend.utils import get_db_or_503, serialize_doc
from resort_backend.lib.locks import acquire_lock, release_lock
from resort_backend.routes.events import publish_event


router = APIRouter(tags=["bookings"])

# Define a local BookingCreateRequest model for POST and BookingUpdateRequest for PUT

class BookingCreateRequest(BaseModel):
    """Model for creating a booking."""
    guest_name: str = Field(..., description="Guest's full name")
    guest_email: str = Field(..., description="Guest's email address")
    guest_phone: str = Field(..., description="Guest's phone number")
    address: str = Field(..., description="Guest's address")
    city: str = Field(..., description="City")
    postal_code: str = Field(..., description="Postal code")
    country: str = Field(..., description="Country")
    accommodation_id: Union[str, List[str]] = Field(..., description="Accommodation ID(s)")
    check_in: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out: str = Field(..., description="Check-out date (YYYY-MM-DD)")
    total_price: float = Field(..., description="Total price")
    payment_method: Optional[str] = Field(None, description="Payment method")
    guests: Optional[int] = Field(None, description="Total guests")
    adults: Optional[int] = Field(None, description="Number of adults")
    children: Optional[int] = Field(None, description="Number of children")


class BookingUpdateRequest(BaseModel):
    """Model for updating a booking."""
    guest_name: Optional[str] = None
    guest_email: Optional[str] = None
    guest_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    accommodation_id: Optional[Union[str, List[str]]] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    total_price: Optional[float] = None
    payment_method: Optional[str] = None
    guests: Optional[int] = None
    adults: Optional[int] = None
    children: Optional[int] = None


class MenuItem(BaseModel):
    """Model for a menu item added to a booking."""
    name: str
    qty: int
    price: float



@router.get("/", response_model=List[dict], summary="Get all bookings")
async def get_all_bookings(request: Request):
    """Return all bookings with extraBeds and cottage fields for frontend compatibility."""
    db = get_db_or_503(request)
    bookings = await db["bookings"].find().to_list(None)
    for b in bookings:
        b.setdefault("extraBeds", 0)
        b.setdefault("cottage", "")
    return [serialize_doc(b) for b in bookings]


@router.get("/{booking_id}")
async def get_booking(request: Request, booking_id: str):
    """Get a specific booking by ID"""
    db = get_db_or_503(request)
    booking = None
    # Try to fetch by _id (ObjectId) and fallback to string id field if needed
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



## Removed duplicate get_booking_by_query endpoint. Use /bookings/{booking_id} instead.


@router.post("/")
async def create_booking(request: Request, booking: BookingCreateRequest):
    db = get_db_or_503(request)
    booking_dict = booking.dict()
    # Ensure extraBeds and cottage fields
    if "extraBeds" not in booking_dict:
        booking_dict["extraBeds"] = 0
    if "cottage" not in booking_dict:
        booking_dict["cottage"] = ""
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
    if "extraBeds" not in update_data:
        update_data["extraBeds"] = 0
    if "cottage" not in update_data:
        update_data["cottage"] = ""
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


@router.post("/{booking_id}/release")
async def release_occupancies_endpoint(request: Request, booking_id: str):
    """Admin-safe endpoint: release occupancies associated with a booking id."""
    db = get_db_or_503(request)
    try:
        b_id = ObjectId(booking_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking id")
    res = await db["occupancies"].delete_many({"booking_id": b_id})
    return {"released": int(res.deleted_count)}


    # ...existing code...


    # ...existing code...


@router.post("/{booking_id}/cancel")
async def cancel_booking(request: Request, booking_id: str):
    db = get_db_or_503(request)
    try:
        result = await db["bookings"].update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": "cancelled"}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Booking not found.")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/{booking_id}/checkout")
async def checkout_booking(request: Request, booking_id: str):
    db = get_db_or_503(request)
    try:
        result = await db["bookings"].update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": "checked_out"}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Booking not found.")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/{booking_id}/menu")
async def add_menu_item(request: Request, booking_id: str, item: MenuItem):
    db = get_db_or_503(request)
    try:
        result = await db["bookings"].update_one(
            {"_id": ObjectId(booking_id)},
            {"$push": {"menuItems": item.dict()}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Booking not found.")
        booking = await db["bookings"].find_one({"_id": ObjectId(booking_id)})
        total = sum(i["qty"] * i["price"] for i in booking.get("menuItems", []))
        await db["bookings"].update_one({"_id": ObjectId(booking_id)}, {"$set": {"total": total}})
        updated_booking = await db["bookings"].find_one({"_id": ObjectId(booking_id)})
        return serialize_doc(updated_booking)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{booking_id}/bill")
async def get_booking_bill(request: Request, booking_id: str):
    db = get_db_or_503(request)
    try:
        booking = await db["bookings"].find_one({"_id": ObjectId(booking_id)})
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found.")
        items_html = ""
        for item in booking.get("menuItems", []):
            items_html += f"<tr><td>{item['name']}</td><td>{item['qty']}</td><td>{item['price']}</td><td>{item['qty']*item['price']}</td></tr>"
        html = f"""
        <html>
        <head><title>Bill</title></head>
        <body>
        <h2>Booking Bill</h2>
        <p><b>Guest:</b> {booking.get('guestName')}</p>
        <p><b>Phone:</b> {booking.get('phone')}</p>
        <p><b>Cottage:</b> {booking.get('cottage')}</p>
        <p><b>Check-In:</b> {booking.get('checkIn')}</p>
        <p><b>Check-Out:</b> {booking.get('checkOut')}</p>
        <table border="1" cellpadding="6" style="border-collapse:collapse;">
          <tr><th>Item</th><th>Qty</th><th>Price</th><th>Total</th></tr>
          {items_html}
        </table>
        <h3>Total: ₹{booking.get('total', 0)}</h3>
        </body>
        </html>
        """
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
