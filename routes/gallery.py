
from fastapi import APIRouter, HTTPException, Request, Depends, Form, File, UploadFile
from fastapi.responses import JSONResponse

from pydantic import BaseModel
from typing import Optional
from resort_backend.utils import get_db_or_503, serialize_doc
from datetime import datetime
import os
from bson import ObjectId


router = APIRouter(tags=["gallery"])


class GalleryCreateRequest(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None
    visible: Optional[bool] = True

class GalleryItemResponse(BaseModel):
    id: str
    title: Optional[str] = None
    caption: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    visible: Optional[bool] = None
    image_url: Optional[str] = None
    created_at: Optional[str] = None

# FIX: Register the route as "/gallery" (no trailing slash)
@router.get("/", response_model=list[GalleryItemResponse])
async def get_gallery(request: Request, category: str = None, visible: Optional[bool] = None):
    """
    Returns all gallery items (images and videos) in a consistent format.
    Supports filtering by category and visible flag.
    """
    db = get_db_or_503(request)
    query = {}
    if category:
        query["category"] = category
    if visible is not None:
        query["visible"] = {"$ne": False} if visible else False
    items = await db["gallery"].find(query).to_list(None)

    def norm(item):
        doc = serialize_doc(item)
        doc["id"] = str(doc.get("_id"))
        doc["title"] = doc.get("title")
        doc["caption"] = doc.get("caption")
        doc["description"] = doc.get("description")
        # Prefer explicit url field, fallback to imageUrl if present
        doc["url"] = doc.get("url") or doc.get("imageUrl") or doc.get("image_url")
        doc["type"] = doc.get("type")
        doc["category"] = doc.get("category")
        doc["visible"] = doc.get("visible", True)
        doc["image_url"] = (
            doc.get("image_url")
            or doc.get("imageUrl")
            or doc.get("thumbnail")
            or doc.get("image")
            or (doc.get("images")[0] if isinstance(doc.get("images"), list) and doc.get("images") else None)
        )
        doc["created_at"] = doc.get("created_at")
        doc = {k: doc[k] for k in GalleryItemResponse.__fields__.keys()}
        return doc

    return [norm(i) for i in items]


@router.get("/", response_class=JSONResponse)
async def list_gallery(request: Request, category: Optional[str] = None, visible: Optional[bool] = None, limit: int = 50, skip: int = 0):
    db = get_db_or_503(request)
    query = {}
    if category:
        query["category"] = category
    # Treat missing `isVisible` as visible in legacy data: when visible=True,
    # include documents that either have isVisible=True or have no isVisible field.
    if visible is not None:
        if visible:
            query["$or"] = [{"isVisible": True}, {"isVisible": {"$exists": False}}]
        else:
            # explicit false: only return documents with isVisible set to False
            query["isVisible"] = False

    try:
        cursor = db.gallery.find(query).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to query gallery collection")

    serialized = [serialize_doc(d) for d in items]
    # Map to public shape expected by frontend
    out = []
    for doc in serialized:
        caption = doc.get("caption") or doc.get("title") or doc.get("description") or ""
        description = doc.get("description") or ""
        imageUrl = doc.get("imageUrl") or doc.get("image") or (doc.get("media") and doc.get("media")[0] if isinstance(doc.get("media"), list) and len(doc.get("media"))>0 else None)
        category_val = doc.get("category") or doc.get("categoryName") or ""
        # If imageUrl is a relative path (e.g. /uploads/...), prefix with request.base_url so
        # browser loads the image from the backend origin rather than the frontend origin.
        if imageUrl and isinstance(imageUrl, str) and imageUrl.startswith('/'):
            imageUrl = str(request.base_url).rstrip('/') + imageUrl

        out.append({
            "id": doc.get("id"),
            "caption": caption,
            "description": description,
            "imageUrl": imageUrl,
            "category": category_val,
            "isVisible": doc.get("isVisible", True),
            "createdAt": doc.get("createdAt"),
        })

    return out


@router.get("/{item_id}")
async def get_gallery_item(request: Request, item_id: str):
    db = get_db_or_503(request)
    try:
        doc = await db.gallery.find_one({"_id": ObjectId(item_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_doc(doc)




@router.put("/{item_id}")
async def update_gallery_item(request: Request, item_id: str, payload: dict):
    db = get_db_or_503(request)
    payload["updatedAt"] = datetime.utcnow()
    # do not allow _id changes
    payload.pop("id", None)
    payload.pop("_id", None)
    # Allow updating the url field
    update_fields = {k: v for k, v in payload.items() if k in ["title", "caption", "description", "type", "category", "visible", "url", "image_url", "imageUrl"]}
    try:
        res = await db.gallery.update_one({"_id": ObjectId(item_id)}, {"$set": update_fields})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.gallery.find_one({"_id": ObjectId(item_id)})
    return serialize_doc(doc)


@router.delete("/{item_id}")
async def delete_gallery_item(request: Request, item_id: str):
    db = get_db_or_503(request)
    try:
        res = await db.gallery.delete_one({"_id": ObjectId(item_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True}

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '../../uploads/gallery')
os.makedirs(UPLOAD_DIR, exist_ok=True)



@router.post("/", response_model=GalleryItemResponse)
async def create_gallery_item_json(data: GalleryCreateRequest, request: Request):
    db = get_db_or_503(request)
    doc = data.dict()
    doc["createdAt"] = datetime.utcnow()
    doc["updatedAt"] = datetime.utcnow()
    # For compatibility, also set imageUrl/image_url fields if url is present
    if doc.get("url"):
        doc["imageUrl"] = doc["url"]
        doc["image_url"] = doc["url"]
        # Auto-detect video by file extension if type is not set
        video_exts = [".mp4", ".webm", ".ogg", ".mov", ".avi", ".mkv"]
        url_lower = doc["url"].lower()
        if not doc.get("type") and any(url_lower.endswith(ext) for ext in video_exts):
            doc["type"] = "video"
    res = await db.gallery.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize_doc(doc)