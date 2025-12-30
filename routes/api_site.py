from fastapi import APIRouter, Request
from resort_backend.utils import get_db_or_503, serialize_doc

router = APIRouter(prefix="/api", tags=["api-site"])


@router.get("/site")
async def get_site_config(request: Request):
    db = get_db_or_503(request)
    # Try to read a single site config document from `site` collection
    try:
        doc = await db["site"].find_one({})
    except Exception:
        doc = None
    if not doc:
        # Fallback minimal config
        return {"siteName": "Resort", "apiBase": "/api"}
    return serialize_doc(doc)
