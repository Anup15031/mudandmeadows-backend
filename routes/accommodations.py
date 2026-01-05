from fastapi import APIRouter, HTTPException, Request
from resort_backend.models import Accommodation
from bson import ObjectId
from datetime import datetime
from resort_backend.utils import get_db_or_503, serialize_doc
from resort_backend.routes.events import publish_event

router = APIRouter(tags=["accommodations"])

@router.get("/")
async def get_all_accommodations(request: Request):
    """Get all accommodations"""
    db = get_db_or_503(request)
    try:
        accommodations = await db["accommodations"].find().to_list(None)
        out = []
        for acc in accommodations:
            acc_doc = serialize_doc(acc)
            # attach related rooms if any (rooms may store accommodation_id as ObjectId or string)
            try:
                rooms_cursor = db["rooms"].find({"$or": [{"accommodation_id": acc.get("_id")}, {"accommodation_id": str(acc.get("_id"))}]})
                rooms = await rooms_cursor.to_list(length=None)
                acc_doc["rooms"] = [serialize_doc(r) for r in rooms]
                # expose adult/child capacity fields for rooms
                for r in acc_doc["rooms"]:
                    try:
                        if r.get("capacity_adults") is not None or r.get("capacity_children") is not None:
                            r["capacity_adults"] = int(r.get("capacity_adults") or r.get("capacity") or r.get("sleeps") or 0)
                            r["capacity_children"] = int(r.get("capacity_children") or 0)
                            r["capacity"] = r["capacity_adults"] + r["capacity_children"]
                    except Exception:
                        pass
            except Exception:
                acc_doc["rooms"] = []
            out.append(acc_doc)
        return out
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch accommodations")

@router.get("/{accommodation_id}")
async def get_accommodation(request: Request, accommodation_id: str):
    """Get a specific accommodation by ID"""
    db = get_db_or_503(request)
    try:
        accommodation = await db["accommodations"].find_one({"_id": ObjectId(accommodation_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid accommodation id")
    if not accommodation:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    out = serialize_doc(accommodation)
    # attach related rooms for this accommodation
    try:
        rooms_cursor = db["rooms"].find({"$or": [{"accommodation_id": accommodation.get("_id")}, {"accommodation_id": str(accommodation.get("_id"))}]})
        rooms = await rooms_cursor.to_list(length=None)
        out["rooms"] = [serialize_doc(r) for r in rooms]
        for r in out["rooms"]:
            try:
                if r.get("capacity_adults") is not None or r.get("capacity_children") is not None:
                    r["capacity_adults"] = int(r.get("capacity_adults") or r.get("capacity") or r.get("sleeps") or 0)
                    r["capacity_children"] = int(r.get("capacity_children") or 0)
                    r["capacity"] = r["capacity_adults"] + r["capacity_children"]
            except Exception:
                pass
    except Exception:
        out["rooms"] = []
    return out

@router.post("/")
async def create_accommodation(request: Request, accommodation: Accommodation):
    """Create a new accommodation"""
    db = get_db_or_503(request)
    acc_dict = accommodation.dict()
    acc_dict["created_at"] = datetime.utcnow()
    result = await db["accommodations"].insert_one(acc_dict)
    created = await db["accommodations"].find_one({"_id": result.inserted_id})
    out = serialize_doc(created)
    # Notify subscribers that rooms/accommodations were updated
    try:
        publish_event({"event": "rooms.updated", "room_id": out.get("id")})
    except Exception:
        pass
    return out

@router.put("/{accommodation_id}")
async def update_accommodation(request: Request, accommodation_id: str, accommodation: Accommodation):
    """Update an accommodation"""
    db = get_db_or_503(request)
    try:
        result = await db["accommodations"].update_one(
            {"_id": ObjectId(accommodation_id)},
            {"$set": accommodation.dict()}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid accommodation id")
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    updated = await db["accommodations"].find_one({"_id": ObjectId(accommodation_id)})
    out = serialize_doc(updated)
    try:
        publish_event({"event": "rooms.updated", "room_id": out.get("id")})
    except Exception:
        pass
    return out

@router.delete("/{accommodation_id}")
async def delete_accommodation(request: Request, accommodation_id: str):
    """Delete an accommodation"""
    db = get_db_or_503(request)
    try:
        result = await db["accommodations"].delete_one({"_id": ObjectId(accommodation_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid accommodation id")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Accommodation not found")
    try:
        publish_event({"event": "rooms.updated", "room_id": accommodation_id})
    except Exception:
        pass
    return {"message": "Accommodation deleted successfully"}
