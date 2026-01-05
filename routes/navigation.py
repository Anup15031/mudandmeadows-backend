from fastapi import APIRouter, Request, HTTPException
from resort_backend.utils import get_db_or_503, serialize_doc
from bson import ObjectId
from datetime import datetime
import logging

router = APIRouter(tags=["navigation"])


@router.get("/")
async def list_navigation(request: Request, public: bool = True):
    """List navigation items.

    By default (`public=true`) only items where `is_visible` is truthy are returned
    (suitable for the public site). Set `?public=false` to retrieve all items
    (admin/debug use).
    """
    logger = logging.getLogger("resort_backend.navigation")
    # try to obtain db, but allow None so we can return a fallback nav for public requests
    try:
        db = get_db_or_503(request)
    except Exception:
        db = None
    q = {}
    if public:
        q["is_visible"] = True
    try:
        # If we don't have a db handle, raise to trigger fallback below
        if db is None:
            raise RuntimeError("db not available")
        # sort by `order` if present to provide consistent navigation ordering
        cursor = db["navigation"].find(q).sort([("order", 1)])
        items = await cursor.to_list(length=None)
    except Exception:
        # DB error: for public requests return a small fallback nav so frontend header stays usable
        if public:
            logger.exception("list_navigation: DB error while fetching navigation, returning fallback nav")
            return [
                {"id": "fallback-cottages", "name": "cottages", "label": "Cottages", "href": "/cottages", "type": "link", "is_visible": True, "order": 10},
                {"id": "fallback-programs", "name": "programs", "label": "Programs", "href": "/programs", "type": "link", "is_visible": True, "order": 20},
                {"id": "fallback-dining", "name": "dining", "label": "Dining", "href": "/dining", "type": "link", "is_visible": True, "order": 30},
                {"id": "fallback-gallery", "name": "gallery", "label": "Gallery", "href": "/gallery", "type": "link", "is_visible": True, "order": 40},
                {"id": "fallback-packages", "name": "packages", "label": "Packages", "href": "/packages", "type": "link", "is_visible": True, "order": 50},
                {"id": "fallback-contact", "name": "contact", "label": "Contact", "href": "/contact", "type": "link", "is_visible": True, "order": 60},
            ]
        raise HTTPException(status_code=500, detail="Failed to fetch navigation items")

    out = [serialize_doc(i) for i in items]
    if public and not out:
        client_host = None
        try:
            client_host = request.client.host
        except Exception:
            client_host = None
        logger.warning("list_navigation: returned 0 visible items for public request (client=%s); returning fallback nav", client_host)
        return [
            {"id": "fallback-cottages", "name": "cottages", "label": "Cottages", "href": "/cottages", "type": "link", "is_visible": True, "order": 10},
            {"id": "fallback-programs", "name": "programs", "label": "Programs", "href": "/programs", "type": "link", "is_visible": True, "order": 20},
            {"id": "fallback-dining", "name": "dining", "label": "Dining", "href": "/dining", "type": "link", "is_visible": True, "order": 30},
            {"id": "fallback-gallery", "name": "gallery", "label": "Gallery", "href": "/gallery", "type": "link", "is_visible": True, "order": 40},
            {"id": "fallback-packages", "name": "packages", "label": "Packages", "href": "/packages", "type": "link", "is_visible": True, "order": 50},
            {"id": "fallback-contact", "name": "contact", "label": "Contact", "href": "/contact", "type": "link", "is_visible": True, "order": 60},
        ]
    return out


@router.post("/")
async def create_navigation(request: Request, payload: dict):
    db = get_db_or_503(request)
    payload["created_at"] = datetime.utcnow()
    res = await db["navigation"].insert_one(payload)
    created = await db["navigation"].find_one({"_id": res.inserted_id})
    return serialize_doc(created)


@router.put("/{item_id}")
async def update_navigation(request: Request, item_id: str, payload: dict):
    db = get_db_or_503(request)
    try:
        res = await db["navigation"].update_one({"_id": ObjectId(item_id)}, {"$set": payload})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Navigation item not found")
    updated = await db["navigation"].find_one({"_id": ObjectId(item_id)})
    return serialize_doc(updated)


@router.delete("/{item_id}")
async def delete_navigation(request: Request, item_id: str):
    db = get_db_or_503(request)
    try:
        res = await db["navigation"].delete_one({"_id": ObjectId(item_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Navigation item not found")
    return {"message": "Deleted"}
