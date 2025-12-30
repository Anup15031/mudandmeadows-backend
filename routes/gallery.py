from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import os
from bson import ObjectId
from datetime import datetime
from resort_backend.utils import get_db_or_503, serialize_doc

router = APIRouter(prefix="/gallery", tags=["gallery"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "gallery")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def admin_key_dep(request: Request):
    """Simple admin key dependency (optional). Reads X-Admin-Key header and compares to env var ADMIN_API_KEY."""
    from os import getenv
    key = request.headers.get("X-Admin-Key")
    expected = getenv("ADMIN_API_KEY")
    if expected is None:
        # no admin key configured — allow in dev
        return True
    if key != expected:
        raise HTTPException(status_code=403, detail="Forbidden")
    return True


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


@router.post("/", dependencies=[Depends(admin_key_dep)])
async def create_gallery_item(request: Request, imageUrl: Optional[str] = Form(None), file: Optional[UploadFile] = File(None), caption: Optional[str] = Form(None), category: Optional[str] = Form(None), isVisible: bool = Form(True)):
    db = get_db_or_503(request)
    final_url = imageUrl
    if file is not None:
        # save file
        filename = f"{int(datetime.utcnow().timestamp())}_{file.filename}"
        dest = os.path.join(UPLOAD_DIR, filename)
        with open(dest, "wb") as f:
            f.write(await file.read())
        # public path served at /uploads/gallery/<filename>
        final_url = f"/uploads/gallery/{filename}"

    if not final_url:
        raise HTTPException(status_code=400, detail="imageUrl or file required")

    doc = {
        "imageUrl": final_url,
        "caption": caption,
        "category": category,
        "isVisible": bool(isVisible),
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }
    res = await db.gallery.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize_doc(doc)


@router.put("/{item_id}", dependencies=[Depends(admin_key_dep)])
async def update_gallery_item(request: Request, item_id: str, payload: dict):
    db = get_db_or_503(request)
    payload["updatedAt"] = datetime.utcnow()
    # do not allow _id changes
    payload.pop("id", None)
    payload.pop("_id", None)
    try:
        res = await db.gallery.update_one({"_id": ObjectId(item_id)}, {"$set": payload})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.gallery.find_one({"_id": ObjectId(item_id)})
    return serialize_doc(doc)


@router.delete("/{item_id}", dependencies=[Depends(admin_key_dep)])
async def delete_gallery_item(request: Request, item_id: str):
    db = get_db_or_503(request)
    try:
        res = await db.gallery.delete_one({"_id": ObjectId(item_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True}
