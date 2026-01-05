from fastapi import APIRouter, HTTPException, Request
from resort_backend.models import Wellness
from bson import ObjectId
from datetime import datetime
from resort_backend.utils import get_db_or_503, serialize_doc

router = APIRouter(tags=["wellness"])

@router.get("/")
async def get_all_wellness(request: Request):
    """Get all wellness services"""
    db = get_db_or_503(request)
    services = await db["wellness"].find().to_list(None)
    return [serialize_doc(s) for s in services]

@router.get("/{wellness_id}")
async def get_wellness(request: Request, wellness_id: str):
    """Get a specific wellness service by ID"""
    db = get_db_or_503(request)
    try:
        wellness = await db["wellness"].find_one({"_id": ObjectId(wellness_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid wellness id")
    if not wellness:
        raise HTTPException(status_code=404, detail="Wellness service not found")
    return serialize_doc(wellness)

@router.post("/")
async def create_wellness(request: Request, wellness: Wellness):
    """Create a new wellness service"""
    db = get_db_or_503(request)
    wellness_dict = wellness.dict()
    wellness_dict["created_at"] = datetime.utcnow()
    result = await db["wellness"].insert_one(wellness_dict)
    created = await db["wellness"].find_one({"_id": result.inserted_id})
    return serialize_doc(created)

@router.put("/{wellness_id}")
async def update_wellness(request: Request, wellness_id: str, wellness: Wellness):
    """Update a wellness service"""
    db = get_db_or_503(request)
    try:
        result = await db["wellness"].update_one(
            {"_id": ObjectId(wellness_id)},
            {"$set": wellness.dict()}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid wellness id")
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Wellness service not found")
    updated = await db["wellness"].find_one({"_id": ObjectId(wellness_id)})
    return serialize_doc(updated)

@router.delete("/{wellness_id}")
async def delete_wellness(request: Request, wellness_id: str):
    """Delete a wellness service"""
    db = get_db_or_503(request)
    try:
        result = await db["wellness"].delete_one({"_id": ObjectId(wellness_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid wellness id")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Wellness service not found")
    return {"message": "Wellness service deleted successfully"}
