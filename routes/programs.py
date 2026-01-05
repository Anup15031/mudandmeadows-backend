from fastapi import APIRouter, HTTPException, Request, Body
from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Any
from resort_backend.utils import get_db_or_503, serialize_doc
import os
import logging

logger = logging.getLogger("resort_backend.programs")
from resort_backend.models import Program

router = APIRouter(tags=["programs"])

@router.get("/")
async def list_programs(request: Request, tag: str | None = None):
    """List programs. Optional query param `tag` filters programs by tag (e.g. ?tag=wellness).

    This endpoint is resilient to different collection names used in databases.
    - If `tag=wellness` will attempt `wellnessPrograms` then `programs`.
    - If `tag=activities` will attempt `activities` then `programs`.
    - Without tag, will return from `programs` if present else combine known program collections.
    """
    db = get_db_or_503(request)
    # Helper to fetch from a collection name if it exists
    async def fetch_from_collection(name: str, q: dict | None = None):
        try:
            # check if collection exists (fast list_collection_names)
            names = await db.list_collection_names()
            if name in names:
                q = q or {}
                docs = await db[name].find(q).to_list(None)
                return [serialize_doc(d) for d in docs]
        except Exception:
            # ignore and return empty
            return []
        return []

    if tag:
        t = tag.lower()
        if t == 'wellness':
            # Prefer explicit wellnessPrograms collection for compatibility
            res = await fetch_from_collection('wellnessPrograms', None)
            if res:
                if os.getenv('DEV_VERBOSE_LOGGING', '').lower() in ('1','true'):
                    logger.info("programs: returning %d docs from wellnessPrograms for tag=%s", len(res), tag)
                return res
            # fallback to programs collection with tag filter
            res2 = await fetch_from_collection('programs', {'tags': {'$in': [tag]}})
            if res2 and os.getenv('DEV_VERBOSE_LOGGING', '').lower() in ('1','true'):
                logger.info("programs: returning %d docs from programs filtered by tag=%s", len(res2), tag)
            return res2
        if t in ('activities', 'resort-activities'):
            res = await fetch_from_collection('activities', None)
            if res:
                if os.getenv('DEV_VERBOSE_LOGGING', '').lower() in ('1','true'):
                    logger.info("programs: returning %d docs from activities for tag=%s", len(res), tag)
                return res
            res2 = await fetch_from_collection('programs', {'tags': {'$in': [tag]}})
            if res2 and os.getenv('DEV_VERBOSE_LOGGING', '').lower() in ('1','true'):
                logger.info("programs: returning %d docs from programs filtered by tag=%s", len(res2), tag)
            return res2

    # No tag: try programs, then wellnessPrograms + activities combined
    res = await fetch_from_collection('programs', None)
    if res:
        if os.getenv('DEV_VERBOSE_LOGGING', '').lower() in ('1','true'):
            logger.info("programs: returning %d docs from programs (no tag)", len(res))
        return res
    # combine known collections
    combined = []
    w = await fetch_from_collection('wellnessPrograms', None)
    a = await fetch_from_collection('activities', None)
    combined += w
    combined += a
    if os.getenv('DEV_VERBOSE_LOGGING', '').lower() in ('1','true'):
        logger.info("programs: combined returned %d docs (wellnessPrograms=%d, activities=%d)", len(combined), len(w), len(a))
    return combined

@router.get("/{program_id}")
async def get_program(request: Request, program_id: str):
    db = get_db_or_503(request)
    # Try to resolve the id across known program-like collections for compatibility
    coll_names = ['programs', 'wellnessPrograms', 'activities']
    oid = None
    try:
        oid = ObjectId(program_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid program id")

    for cname in coll_names:
        try:
            doc = await db[cname].find_one({"_id": oid})
        except Exception:
            doc = None
        if doc:
            return serialize_doc(doc)
    raise HTTPException(status_code=404, detail="Program not found")


@router.get("/debug/collections")
async def debug_collections(request: Request):
    """Return list of collections visible to the connected DB (debug only)."""
    db = get_db_or_503(request)
    try:
        names = await db.list_collection_names()
        return {"collections": names}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to list collections")


@router.get("/debug/sample")
async def debug_sample(request: Request, col: str | None = None, limit: int = 5):
    """Return up to `limit` sample documents from a collection for debugging.

    Example: `/programs/debug/sample?col=wellnessPrograms&limit=3`
    """
    db = get_db_or_503(request)
    if not col:
        raise HTTPException(status_code=400, detail="col query parameter required")
    try:
        names = await db.list_collection_names()
        if col not in names:
            raise HTTPException(status_code=404, detail=f"Collection {col} not found")
        docs = await db[col].find().limit(limit).to_list(length=limit)
        return [serialize_doc(d) for d in docs]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch sample documents")

@router.post("/")
async def create_program(request: Request, program: Program):
    db = get_db_or_503(request)
    doc = program.dict()
    doc["created_at"] = datetime.utcnow()
    res = await db["programs"].insert_one(doc)
    created = await db["programs"].find_one({"_id": res.inserted_id})
    return serialize_doc(created)

@router.put("/{program_id}")
async def update_program(request: Request, program_id: str, program: Program):
    db = get_db_or_503(request)
    try:
        res = await db["programs"].update_one({"_id": ObjectId(program_id)}, {"$set": program.dict()})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid program id")
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Program not found")
    updated = await db["programs"].find_one({"_id": ObjectId(program_id)})
    return serialize_doc(updated)

@router.delete("/{program_id}")
async def delete_program(request: Request, program_id: str):
    db = get_db_or_503(request)
    try:
        res = await db["programs"].delete_one({"_id": ObjectId(program_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid program id")
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Program not found")
    return {"message": "Program deleted"}


@router.post("/recommend")
async def recommend_programs(request: Request, payload: Dict[str, Any] = Body(...)):
    """Return top recommended programs based on guestProfile and stayDates.

    payload example: { "guestPreferences": ["yoga","detox"], "stayDays": 3 }
    """
    db = get_db_or_503(request)
    prefs = payload.get("guestPreferences", []) or []
    stay_days = int(payload.get("stayDays") or 0)

    # simple scoring: +2 if tag matches preference, +1 if duration <= stay_days
    programs = await db["programs"].find().to_list(None)
    scored = []
    for p in programs:
        score = 0
        tags = p.get("tags") or []
        for t in tags:
            if any(pref.lower() in str(t).lower() for pref in prefs):
                score += 2
        dur = p.get("duration_days") or 0
        if stay_days and dur and dur <= stay_days:
            score += 1
        # availability: check capacity vs bookings referencing program in same dates if provided
        available = True
        avail_slots = None
        if p.get("capacity") is not None:
            avail_slots = int(p.get("capacity"))
            # don't compute booked slots here for simplicity; caller can verify when reserving
        scored.append({"program": serialize_doc(p), "score": score, "available_slots": avail_slots})

    scored = sorted(scored, key=lambda x: x["score"], reverse=True)
    return scored[:3]
