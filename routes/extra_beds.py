from fastapi import APIRouter, HTTPException, Request
from bson import ObjectId
from datetime import datetime
from resort_backend.utils import get_db_or_503, serialize_doc
from resort_backend.models import ExtraBedRequest
from resort_backend.routes.events import publish_event

router = APIRouter(tags=["extra-beds"])


@router.get("/")
async def list_extra_beds(request: Request):
    db = get_db_or_503(request)
    items = await db["extra_bed"].find().to_list(None)
    return [serialize_doc(i) for i in items]


@router.get("/{item_id}")
async def get_extra_bed(request: Request, item_id: str):
    db = get_db_or_503(request)
    try:
        item = await db["extra_bed"].find_one({"_id": ObjectId(item_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_doc(item)


@router.get("/for-accommodation/{accommodation_id}")
async def extra_beds_for_accommodation(request: Request, accommodation_id: str):
    db = get_db_or_503(request)
    items = await db["extra_bed"].find({"accommodation_id": accommodation_id}).to_list(None)
    return [serialize_doc(i) for i in items]


@router.post("/request")
async def request_extra_bed(request: Request, req: ExtraBedRequest):
    db = get_db_or_503(request)
    obj = req.dict()
    obj["requested_at"] = datetime.utcnow()
    result = await db["extra_bed_requests"].insert_one(obj)
    created = await db["extra_bed_requests"].find_one({"_id": result.inserted_id})
    out = serialize_doc(created)
    try:
        publish_event({"event": "extra_bed.requested", "request_id": out.get("id")})
    except Exception:
        pass
    return out
