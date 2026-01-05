from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

from resort_backend.utils import get_db_or_503

router = APIRouter(tags=["contact"])

class ContactInfo(BaseModel):
    location: Optional[str] = None
    reservations: Optional[str] = None
    email: Optional[str] = None
    reception_hours: Optional[str] = None

class MapInfo(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    embed_url: Optional[str] = None

class AboutInfo(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    highlights: Optional[List[str]] = None

class SocialInfo(BaseModel):
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    twitter: Optional[str] = None

class ContactMessage(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    subject: Optional[str] = None
    message: str
    siteName: Optional[str] = None
    apiBase: Optional[str] = None
    theme: Optional[str] = None
    contactEmail: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    contact: Optional[ContactInfo] = None
    map: Optional[MapInfo] = None
    about: Optional[AboutInfo] = None
    social: Optional[SocialInfo] = None
    created_at: Optional[datetime] = None

    class Config:
        extra = "allow"

@router.post("/contact")
async def create_contact_message(request: Request, msg: ContactMessage):
    db = get_db_or_503(request)
    doc = msg.dict(exclude_unset=True)
    doc["created_at"] = datetime.utcnow()
    await db["contact_messages"].insert_one(doc)
    return {"success": True, "message": "Message received."}
