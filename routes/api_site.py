from fastapi import APIRouter, Request, HTTPException
from utils import get_db_or_503, serialize_doc

router = APIRouter(tags=["site"])


@router.get("/")
async def get_site(request: Request):
    db = get_db_or_503(request)
    site = await db["site"].find_one(sort=[("createdAt", -1)])
    if not site:
        raise HTTPException(status_code=404, detail="Site config not found")
    return serialize_doc(site)
