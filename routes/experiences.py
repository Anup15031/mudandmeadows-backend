from fastapi import APIRouter, HTTPException, Request
from resort_backend.models import Experience
from bson import ObjectId
from datetime import datetime
from resort_backend.utils import get_db_or_503, serialize_doc

router = APIRouter(tags=["experiences"])

@router.get("/")
async def get_all_experiences(request: Request):
    """Get all experiences"""
    db = get_db_or_503(request)
    experiences = await db["experiences"].find().to_list(None)
    return [serialize_doc(exp) for exp in experiences]

@router.get("/{experience_id}")
async def get_experience(request: Request, experience_id: str):
    """Get a specific experience by ID"""
    db = get_db_or_503(request)
    try:
        experience = await db["experiences"].find_one({"_id": ObjectId(experience_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid experience id")
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found")
    return serialize_doc(experience)

@router.post("/")
async def create_experience(request: Request, experience: Experience):
    """Create a new experience"""
    db = get_db_or_503(request)
    exp_dict = experience.dict()
    exp_dict["created_at"] = datetime.utcnow()
    result = await db["experiences"].insert_one(exp_dict)
    created = await db["experiences"].find_one({"_id": result.inserted_id})
    return serialize_doc(created)

@router.put("/{experience_id}")
async def update_experience(request: Request, experience_id: str, experience: Experience):
    """Update an experience"""
    db = get_db_or_503(request)
    try:
        result = await db["experiences"].update_one(
            {"_id": ObjectId(experience_id)},
            {"$set": experience.dict()}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid experience id")
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Experience not found")
    updated = await db["experiences"].find_one({"_id": ObjectId(experience_id)})
    return serialize_doc(updated)

@router.delete("/{experience_id}")
async def delete_experience(request: Request, experience_id: str):
    """Delete an experience"""
    db = get_db_or_503(request)
    try:
        result = await db["experiences"].delete_one({"_id": ObjectId(experience_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid experience id")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Experience not found")
    return {"message": "Experience deleted successfully"}
