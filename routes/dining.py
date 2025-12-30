from fastapi import APIRouter, HTTPException, Request
from resort_backend.utils import get_db_or_503, serialize_doc

router = APIRouter(prefix="/api", tags=["dining"])

@router.get("/dining")
async def get_dining(request: Request):
    """
    Returns all menu items from the 'menu' or 'menu_items' collection.
    """
    db = get_db_or_503(request)
    items = []
    try:
        items = await db["menu"].find().to_list(None)
        if not items:
            items = await db["menu_items"].find().to_list(None)
    except Exception:
        pass
    return [serialize_doc(i) for i in items]
