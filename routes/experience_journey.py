from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import List
from utils import get_db_or_503

router = APIRouter(tags=["experience_journey"])

class ExperienceJourneySection(BaseModel):
    id: str
    title: str
    text: str
    image: str




@router.get("/api/experience-journey", response_model=List[ExperienceJourneySection])
async def get_experience_journey(request: Request):
    db = get_db_or_503(request)
    # Fetch all journey sections from the 'experience' collection
    docs = await db["experience"].find().to_list(None)
    # Only return id, title, text, image fields for journey page
    return [
        {
            "id": doc.get("id", str(doc.get("_id"))),
            "title": doc.get("title", ""),
            "text": doc.get("text", ""),
            "image": doc.get("image", ""),
        }
        for doc in docs
        if doc.get("id") and doc.get("title") and doc.get("text") and doc.get("image")
    ]
