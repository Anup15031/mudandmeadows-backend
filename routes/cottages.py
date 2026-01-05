from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime
from resort_backend.utils import get_db_or_503, serialize_doc
from typing import Optional

router = APIRouter(tags=["cottages"])

# Pydantic model for cottage
class CottageModel(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    images: Optional[list[str]] = None  # List of image URLs
    amenities: Optional[list[str]] = None
    size: Optional[float] = None  # in sqm
    view: Optional[str] = None
    guests: Optional[int] = None
    available: Optional[bool] = True
    maintenance: Optional[bool] = False

class CottageUpdateModel(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    images: Optional[list[str]] = None
    amenities: Optional[list[str]] = None
    size: Optional[float] = None
    view: Optional[str] = None
    guests: Optional[int] = None
    available: Optional[bool] = None
    maintenance: Optional[bool] = None

@router.get("/all")
async def get_all_cottages_admin(request: Request):
    db = get_db_or_503(request)
    try:
        cottages = await db["cottages"].find().to_list(None)
        return [serialize_doc(c) for c in cottages]
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch cottages")

@router.post("/add", status_code=201)
async def create_cottage(request: Request, cottage: CottageModel):
    db = get_db_or_503(request)
    try:
        result = await db["cottages"].insert_one(cottage.dict())
        new_cottage = await db["cottages"].find_one({"_id": result.inserted_id})
        return serialize_doc(new_cottage)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/{cottage_id}")
async def update_cottage(request: Request, cottage_id: str, cottage: CottageUpdateModel):
    db = get_db_or_503(request)
    try:
        update_data = {k: v for k, v in cottage.dict().items() if v is not None}
        result = await db["cottages"].update_one({"_id": ObjectId(cottage_id)}, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Cottage not found.")
        updated_cottage = await db["cottages"].find_one({"_id": ObjectId(cottage_id)})
        return serialize_doc(updated_cottage)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/{cottage_id}", status_code=204)
async def delete_cottage(request: Request, cottage_id: str):
    db = get_db_or_503(request)
    try:
        result = await db["cottages"].delete_one({"_id": ObjectId(cottage_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Cottage not found.")
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/")
async def get_all_cottages(
    request: Request,
    availableStart: Optional[str] = Query(None),
    availableEnd: Optional[str] = Query(None)
):
    """Get all cottages (alias for accommodations), optionally filter by availability"""
    db = get_db_or_503(request)
    try:
        cottages = await db["cottages"].find().to_list(None)
        out = [serialize_doc(c) for c in cottages]

        # If no date filter, return all cottages
        if not availableStart or not availableEnd:
            return out

        # Parse dates
        try:
            start_date = datetime.strptime(availableStart, "%Y-%m-%d")
            end_date = datetime.strptime(availableEnd, "%Y-%m-%d")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

        # Get all bookings that overlap with the requested range
        bookings = await db["bookings"].find({
            "$or": [
                {
                    "check_in": {"$lt": availableEnd},
                    "check_out": {"$gt": availableStart}
                }
            ]
        }).to_list(None)
        booked_ids = set()
        for b in bookings:
            # booking may be for one or multiple cottages
            acc_ids = b.get("accommodation_id")
            if isinstance(acc_ids, list):
                booked_ids.update(str(aid) for aid in acc_ids)
            elif acc_ids:
                booked_ids.add(str(acc_ids))

        # Only return cottages that are NOT booked in the given range
        available_cottages = [c for c in out if str(c.get("_id") or c.get("id")) not in booked_ids]
        # Optionally, add 'available' property for frontend
        for c in available_cottages:
            c['available'] = True
        return available_cottages
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch cottages")

@router.get("/{cottage_id}")
async def get_cottage(request: Request, cottage_id: str):
    """Get a specific cottage by ID (alias for accommodation)"""
    db = get_db_or_503(request)
    try:
        cottage = await db["cottages"].find_one({"_id": ObjectId(cottage_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid cottage id")
    if not cottage:
        raise HTTPException(status_code=404, detail="Cottage not found")
    out = serialize_doc(cottage)
    # Ensure 'title' property exists for frontend compatibility
    if 'title' not in out or not out['title']:
        out['title'] = out.get('name', '')
    return out