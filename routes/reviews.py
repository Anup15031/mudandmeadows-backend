from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from resort_backend.database import get_db
from typing import List
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()

class Review(BaseModel):
    reviewer: str = Field(..., example="John Doe")
    rating: int = Field(..., ge=1, le=5, example=5)
    comment: str = Field(..., example="Great experience!")
    date: datetime = Field(default_factory=datetime.utcnow)

@router.get("/reviews", response_model=List[Review])
async def get_reviews(db: AsyncIOMotorDatabase = Depends(get_db)):
    reviews = await db.reviews.find().to_list(100)
    return reviews

@router.post("/reviews", response_model=Review)
async def add_review(review: Review, db: AsyncIOMotorDatabase = Depends(get_db)):
    review_dict = review.dict()
    await db.reviews.insert_one(review_dict)
    return review_dict
