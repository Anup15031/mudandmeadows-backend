from fastapi import APIRouter, Request, HTTPException
from resort_backend.utils import get_db_or_503, serialize_doc

router = APIRouter(tags=["reviews"])

@router.get("/")
async def get_reviews(request: Request):
    """
    Fetch all reviews from the database.
    Uses get_db_or_503 to ensure db is available, else returns 503.
    """
    db = get_db_or_503(request)
    try:
        reviews = await db["reviews"].find().to_list(100)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch reviews")
    return [serialize_doc(r) for r in reviews]
