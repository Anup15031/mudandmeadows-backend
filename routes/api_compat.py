from fastapi import APIRouter, Request, HTTPException, Body, Response
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter
from fastapi.responses import PlainTextResponse
from typing import Optional, List
from collections import Counter
from datetime import datetime
from resort_backend.utils import get_db_or_503, serialize_doc
from bson import ObjectId
from pydantic import BaseModel
import itertools
import random
import string
import re
import json
import logging

router = APIRouter(tags=["api_compat"])
logger = logging.getLogger(__name__)


class BookingRequest(BaseModel):
    guest_name: str
    guest_email: str
    guests: Optional[int] = None
    adults: Optional[int] = None
    children: Optional[int] = None
    check_in: str
    check_out: str
    guest_phone: Optional[str] = None
    allow_extra_beds: Optional[bool] = False
    preferred_room_types: Optional[List[str]] = None
    selected_cottages: Optional[List[str]] = None
    selected_programs: Optional[List[str]] = None
    price_breakdown: Optional[dict] = None
    extra_beds_qty: Optional[int] = 0
    extra_beds_qty: Optional[int] = 0
    # Optional single extra bed selection (compatibility) and quantity
    extraBedId: Optional[str] = None
    extraBedQuantity: Optional[int] = 0

def gen_reference():
    return "RB-" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + "-" + ''.join(random.choices(string.digits, k=4))


def _room_capacity(room: dict, allow_extra_beds: bool) -> int:
    cap = 0
    if room is None:
        return 0
    # Prefer explicit adults/children capacity fields if present
    if "capacity_adults" in room or "capacity_children" in room:
        a = int(room.get("capacity_adults") or 0)
        c = int(room.get("capacity_children") or 0)
        cap = a + c
        if allow_extra_beds:
            eb = room.get("extra_beds") if room.get("extra_beds") is not None else room.get("extra_bedding")
            try:
                cap += int(eb) if eb is not None else 0
            except Exception:
                cap += 0
        return cap
    if "capacity" in room and isinstance(room["capacity"], int):
        cap = room["capacity"]
    elif "sleeps" in room and isinstance(room["sleeps"], int):
        cap = room["sleeps"]
    else:
        cap = 0
        bc = room.get("bedConfig") or []
        for b in bc:
            cnt = b.get("count") or 1
            try:
                cap += int(cnt)
            except Exception:
                cap += 1
    if allow_extra_beds:
        eb = room.get("extra_beds") if room.get("extra_beds") is not None else room.get("extra_bedding")
        if isinstance(eb, int):
            cap += eb
        else:
            cap += 1
    return cap


def allocate_rooms(candidates, guests: int, allow_extra_beds: bool = False, preferred_room_types=None, max_k: int = 4):
    if guests <= 0:
        return []
    filtered = []
    if preferred_room_types:
        prefs = set([p.lower() for p in preferred_room_types])
        for r in candidates:
            slug = (r.get("slug") or "").lower()
            rtype = (r.get("type") or "").lower()
            if slug in prefs or rtype in prefs:
                filtered.append(r)
        if not filtered:
            filtered = list(candidates)
    else:
        filtered = list(candidates)

    annotated = []
    for r in filtered:
        cap = _room_capacity(r, allow_extra_beds)
        price = r.get("price_per_night") or r.get("pricePerNight") or r.get("price") or 0
        annotated.append({"room": r, "cap": cap, "price": price})

    singles = [a for a in annotated if a["cap"] >= guests]
    if singles:
        pick = min(singles, key=lambda a: a["price"])
        return [pick["room"]["_id"]]

    n = len(annotated)
    max_k = min(max_k, n)
    best_combo = None
    best_k = None
    best_price = None
    for k in range(2, max_k + 1):
        for combo in itertools.combinations(annotated, k):
            cap = sum(c["cap"] for c in combo)
            if cap >= guests:
                price = sum(c["price"] for c in combo)
                if best_combo is None or k < best_k or (k == best_k and price < best_price):
                    best_combo = combo
                    best_k = k
                    best_price = price
        if best_combo is not None:
            break
    if best_combo is not None:
        return [c["room"]["_id"] for c in best_combo]

    sorted_cand = sorted(annotated, key=lambda a: (-a["cap"], a["price"]))
    picked = []
    total = 0
    for a in sorted_cand:
        if total >= guests:
            break
        picked.append(a["room"]["_id"])
        total += a["cap"]
    if total < guests:
        return []
    return picked


@router.get("/site/site-config.js")
async def site_config_js():
    config = {"apiBase": "/api", "siteName": "Resort"}
    body = "window.__SITE_CONFIG__ = " + json.dumps(config) + ";"
    return Response(content=body, media_type="application/javascript")



# NOTE: cottages lookup was unified below. Earlier duplicate handler removed.


@router.get("/dining")
async def dining_menu(request: Request):
    db = get_db_or_503(request)
    docs = await db["menu"].find().to_list(None)
    return [serialize_doc(d) for d in docs]


@router.post("/dining/ensure")
async def dining_ensure(request: Request):
    db = get_db_or_503(request)
    # Simple ensure: if menu empty, copy from menu_items
    cnt = await db["menu"].count_documents({})
    if cnt == 0:
        items = await db["menu_items"].find().to_list(None)
        if items:
            for it in items:
                it.pop("_id", None)
            await db["menu"].insert_many(items)
    return {"ok": True}


@router.get("/programs")
async def programs_list(request: Request):
    db = get_db_or_503(request)
    # If a tag query param is provided and equals 'wellness', return a wrapped
    # { value: [...], Count: N } payload sourced from `wellnessPrograms` when available.
    tag = request.query_params.get('tag') if request.query_params else None
    if tag:
        t = tag.lower()
        if t == 'wellness':
            try:
                names = await db.list_collection_names()
            except Exception:
                raise HTTPException(status_code=500, detail="Failed to list collections")

        async def map_doc_local(d: dict):
            try:
                doc = serialize_doc(d)
            except Exception:
                doc = dict(d)
            title = doc.get("title") or doc.get("name") or doc.get("programName") or ""
            description = doc.get("description") or doc.get("summary") or doc.get("details") or ""
            duration = doc.get("duration") or (str(doc.get("duration_days")) + " days" if doc.get("duration_days") else doc.get("length") or "")
            price = doc.get("price") or doc.get("price_inr") or doc.get("cost") or doc.get("amount") or 0
            try:
                if isinstance(price, (float, int)):
                    price_val = int(price)
                else:
                    price_val = int(float(str(price)))
            except Exception:
                price_val = 0
            image = doc.get("image")
            if not image:
                imgs = doc.get("images") or doc.get("media") or []
                if isinstance(imgs, list) and len(imgs) > 0:
                    image = imgs[0]
            return {
                "title": title,
                "description": description,
                "duration": duration,
                "price": price_val,
                "image": image,
            }

        if "wellnessPrograms" in (await db.list_collection_names()):
            try:
                docs = await db["wellnessPrograms"].find().to_list(None)
            except Exception:
                raise HTTPException(status_code=500, detail="Failed to query wellnessPrograms")
            out = [await map_doc_local(d) for d in docs]
            return {"value": out, "Count": len(out)}
            # Fallback: continue to normal behavior below if wellnessPrograms not present
        if t in ('activities', 'resort-activities'):
            # Return activities collection in a simplified public form
            async def map_activity(d: dict):
                try:
                    doc = serialize_doc(d)
                except Exception:
                    doc = dict(d)
                return {
                    "title": doc.get("title") or doc.get("name") or "",
                    "description": doc.get("description") or doc.get("summary") or "",
                    "schedule": doc.get("schedule") or doc.get("time") or "",
                    "location": doc.get("location") or "",
                    "price": doc.get("price") or 0,
                    "imageUrl": doc.get("imageUrl") or doc.get("image") or (doc.get("images") or (doc.get("media") or []) ) and ( (doc.get("images") or (doc.get("media") or []) )[0] if isinstance((doc.get("images") or (doc.get("media") or [])), list) and len((doc.get("images") or (doc.get("media") or [])))>0 else None),
                    "id": doc.get("id") or doc.get("_id")
                }

            if "activities" in (await db.list_collection_names()):
                try:
                    docs = await db["activities"].find().to_list(None)
                except Exception:
                    raise HTTPException(status_code=500, detail="Failed to query activities")
                out = [await map_activity(d) for d in docs]
                return out
            # else fallthrough to normal behavior

    # Try to return from `programs` if present; else combine wellnessPrograms + activities
    try:
        names = await db.list_collection_names()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to list collections")

    async def fetch(name: str):
        if name in names:
            docs = await db[name].find().to_list(None)
            return [serialize_doc(d) for d in docs]
        return []

    res = await fetch("programs")
    if res:
        return res
    combined = []
    combined += await fetch("wellnessPrograms")
    combined += await fetch("activities")
    return combined



@router.get('/sitemap.xml')
async def sitemap_xml(request: Request):
    """Dynamic sitemap generated from accommodations and rooms collections."""
    db = get_db_or_503(request)
    frontend = os.environ.get('FRONTEND_URL') or str(request.base_url).rstrip('/')
    urls = []
    try:
        accs = await db['accommodations'].find().to_list(length=None)
        for a in accs:
            s = a.get('slug') or a.get('id') or (str(a.get('_id')) if a.get('_id') else None)
            if s:
                urls.append(f"{frontend}/rooms/{s}")
    except Exception:
        pass
    try:
        rooms = await db['rooms'].find().to_list(length=None)
        for r in rooms:
            s = r.get('slug') or r.get('id') or (str(r.get('_id')) if r.get('_id') else None)
            if s:
                urls.append(f"{frontend}/rooms/{s}")
    except Exception:
        pass

    # dedupe preserving order
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)

    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in unique:
        xml_parts.append('  <url>')
        xml_parts.append(f'    <loc>{u}</loc>')
        xml_parts.append('    <changefreq>weekly</changefreq>')
        xml_parts.append('    <priority>0.8</priority>')
        xml_parts.append('  </url>')
    xml_parts.append('</urlset>')
    from fastapi.responses import Response
    return Response('\n'.join(xml_parts), media_type='application/xml')


@router.get("/programs/wellness")
async def programs_wellness(request: Request):
    db = get_db_or_503(request)
    try:
        names = await db.list_collection_names()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to list collections")

    # Optional API key protection: if enabled via env, require X-API-KEY header.
    # For developer convenience, do not enforce the API key when running in
    # a non-production environment (ENVIRONMENT != 'production'). This allows
    # local frontend dev servers to call `/api/programs/wellness` without
    # injecting secrets into the client.
    import os
    # This compatibility endpoint intentionally does not enforce the API key.
    # API key enforcement is available on stricter endpoints; keep this route
    # open for development clients to avoid embedding secrets in the frontend.

    async def map_doc(d: dict):
        # Map document fields to expected public schema
        try:
            doc = serialize_doc(d)
        except Exception:
            doc = dict(d)
        title = doc.get("title") or doc.get("name") or doc.get("programName") or ""
        description = doc.get("description") or doc.get("summary") or doc.get("details") or ""
        duration = doc.get("duration") or (str(doc.get("duration_days")) + " days" if doc.get("duration_days") else doc.get("length") or "")
        price = doc.get("price") or doc.get("price_inr") or doc.get("cost") or doc.get("amount") or 0
        # normalize numeric
        try:
            if isinstance(price, (float, int)):
                price_val = int(price)
            else:
                price_val = int(float(str(price)))
        except Exception:
            price_val = 0
        image = doc.get("image")
        if not image:
            imgs = doc.get("images") or doc.get("media") or []
            if isinstance(imgs, list) and len(imgs) > 0:
                image = imgs[0]
        return {
            "title": title,
            "description": description,
            "duration": duration,
            "price": price_val,
            "image": image,
        }

    # Prefer wellnessPrograms collection if it exists
    if "wellnessPrograms" in names:
        try:
            docs = await db["wellnessPrograms"].find().to_list(None)
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to query wellnessPrograms")
        out = []
        for d in docs:
            out.append(await map_doc(d))
        return {"value": out, "Count": len(out)}

    # Fallback: match documents in `programs` with wellness type/tags
    q = {
        "$or": [
            {"type": {"$regex": "wellness", "$options": "i"}},
            {"tags": {"$elemMatch": {"$regex": "wellness", "$options": "i"}}}
        ]
    }
    try:
        docs = await db["programs"].find(q).to_list(None)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to query programs collection")
    out = [await map_doc(d) for d in docs]
    return {"value": out, "Count": len(out)}


@router.get("/rooms/name/{room_name}")
async def rooms_get_by_name(request: Request, room_name: str):
    db = get_db_or_503(request)
    # try combined $or lookup to match name, slug, id, or _id
    query = {
        "$or": [
            {"name": {"$regex": f"^{re.escape(room_name)}$", "$options": "i"}},
            {"slug": room_name},
            {"id": room_name},
            {"_id": room_name}
        ]
    }
    try:
        doc = await db["rooms"].find_one(query)
    except Exception:
        doc = None

    if not doc:
        # try accommodations fallback where an accommodation matches the slug/id/name
        try:
            acc = await db["accommodations"].find_one({"$or": [{"slug": room_name}, {"id": room_name}, {"name": {"$regex": f"^{re.escape(room_name)}$", "$options": "i"}}]})
        except Exception:
            acc = None
        if acc:
            a = serialize_doc(acc)
            try:
                rooms_cursor = db["rooms"].find({"$or": [{"accommodation_id": acc.get("_id")}, {"accommodation_id": str(acc.get("_id"))}]})
                rooms = await rooms_cursor.to_list(length=None)
                a["rooms"] = [serialize_doc(r) for r in rooms] if rooms else []
            except Exception:
                a.setdefault("rooms", [])
            return a
        raise HTTPException(status_code=404, detail="Not found")

    out = serialize_doc(doc)
    if out.get("pricePerNight") is not None and out.get("price_per_night") is None:
        out["price_per_night"] = out.get("pricePerNight")
    if out.get("price") is not None and out.get("price_per_night") is None:
        out["price_per_night"] = out.get("price")
    if out.get("images") is None and out.get("media") is not None:
        out["images"] = out.get("media")
    if out.get("capacity") is None and out.get("sleeps") is not None:
        out["capacity"] = out.get("sleeps")
    if out.get("available") is None:
        out["available"] = True
    out["extraBedAllowed"] = out.get("extraBedAllowed") or out.get("extra_bed_allowed") or False
    out["allowedExtraBedIds"] = out.get("allowedExtraBedIds") or out.get("allowed_extra_bed_ids") or out.get("allowedExtraBeds") or None
    return out

    # If not found in rooms, try accommodations collection (some datasets store items there)
    try:
        acc = await db["accommodations"].find_one({"$or": [
            {"slug": room_name},
            {"id": room_name},
            {"name": {"$regex": f"^{room_name}$", "$options": "i"}}
        ]})
    except Exception:
        acc = None

    if acc:
        # normalize accommodation document to a room-like response the frontend expects
        a = serialize_doc(acc)
        # attach any per-accommodation rooms
        try:
            rooms_cursor = db["rooms"].find({"$or": [{"accommodation_id": acc.get("_id")}, {"accommodation_id": str(acc.get("_id"))}]})
            rooms = await rooms_cursor.to_list(length=None)
            if rooms:
                a["rooms"] = [serialize_doc(r) for r in rooms]
            else:
                a.setdefault("rooms", [])
        except Exception:
            a.setdefault("rooms", [])
        return a

    raise HTTPException(status_code=404, detail="Not found")


@router.get("/dining")
async def dining_menu(request: Request):
    db = get_db_or_503(request)
    docs = await db["menu"].find().to_list(None)
    return [serialize_doc(d) for d in docs]


@router.post("/dining/ensure")
async def dining_ensure(request: Request):
    db = get_db_or_503(request)
    # Simple ensure: if menu empty, copy from menu_items
    cnt = await db["menu"].count_documents({})
    if cnt == 0:
        items = await db["menu_items"].find().to_list(None)
        if items:
            for it in items:
                it.pop("_id", None)
            await db["menu"].insert_many(items)
    return {"ok": True}


@router.get("/programs")
async def programs_list(request: Request):
    db = get_db_or_503(request)
    # Try to return from `programs` if present; else combine wellnessPrograms + activities
    try:
        names = await db.list_collection_names()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to list collections")

    async def fetch(name: str):
        if name in names:
            docs = await db[name].find().to_list(None)
            return [serialize_doc(d) for d in docs]
        return []

    res = await fetch("programs")
    if res:
        return res
    combined = []
    combined += await fetch("wellnessPrograms")
    combined += await fetch("activities")
    return combined





@router.get("/programs/activities")
async def programs_activities(request: Request):
    db = get_db_or_503(request)
    try:
        names = await db.list_collection_names()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to list collections")
    async def map_doc(d: dict):
        try:
            doc = serialize_doc(d)
        except Exception:
            doc = dict(d)
        title = doc.get("title") or doc.get("name") or doc.get("programName") or ""
        description = doc.get("description") or doc.get("summary") or doc.get("details") or ""
        duration = doc.get("duration") or (str(doc.get("duration_days")) + " days" if doc.get("duration_days") else doc.get("length") or "")
        price = doc.get("price") or doc.get("price_inr") or doc.get("cost") or doc.get("amount") or 0
        try:
            if isinstance(price, (float, int)):
                price_val = int(price)
            else:
                price_val = int(float(str(price)))
        except Exception:
            price_val = 0
        image = doc.get("image")
        if not image:
            imgs = doc.get("images") or doc.get("media") or []
            if isinstance(imgs, list) and len(imgs) > 0:
                image = imgs[0]
        # If image is a relative path, prefix with backend base URL so frontend loads from backend
        try:
            if image and isinstance(image, str) and image.startswith("/"):
                base = str(request.base_url).rstrip("/")
                image = base + image
        except Exception:
            pass
        return {
            "title": title,
            "description": description,
            "duration": duration,
            "price": price_val,
            "image": image,
        }

    # Prefer activities collection if it exists
    if "activities" in names:
        try:
            docs = await db["activities"].find().to_list(None)
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to query activities")
        out = [await map_doc(d) for d in docs]
        return {"value": out, "Count": len(out)}

    # Fallback: match documents in `programs` with activity type/tags
    q = {
        "$or": [
            {"type": {"$regex": "activity|activities", "$options": "i"}},
            {"tags": {"$elemMatch": {"$regex": "activity|activities", "$options": "i"}}}
        ]
    }
    try:
        docs = await db["programs"].find(q).to_list(None)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to query programs for activities")
    out = [await map_doc(d) for d in docs]
    return {"value": out, "Count": len(out)}


@router.post("/bookings", status_code=201)
async def create_booking(request: Request, payload: BookingRequest = Body(...), response: Response = None):
    db = get_db_or_503(request)
    try:
        data = payload.dict()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Basic input validation (email format, phone)
    email = data.get("guest_email")
    if email:
        # simple regex: contains @ and a dot after
        if not re.match(r"[^@]+@[^@]+\.[^@]+", str(email)):
            raise HTTPException(status_code=400, detail="Invalid guest_email format")
    phone = data.get("guest_phone")
    if phone:
        digits = re.sub(r"\D", "", str(phone))
        if len(digits) < 6:
            raise HTTPException(status_code=400, detail="Invalid guest_phone")

    try:
        s = datetime.strptime(data.get("check_in"), "%Y-%m-%d")
        e = datetime.strptime(data.get("check_out"), "%Y-%m-%d")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid dates; use YYYY-MM-DD")
    if e <= s:
        raise HTTPException(status_code=400, detail="check_out must be after check_in")

    try:
        guests = int(data.get("guests"))
        if guests <= 0:
            raise ValueError()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid guests count")

    email = data.get("guest_email")
    if not email:
        raise HTTPException(status_code=400, detail="Invalid guest_email")

    # Idempotency: if payment info is present, return existing booking if one already created for this payment
    payment = data.get("payment") or {}
    try:
        pay_pid = payment.get("payment_id") if isinstance(payment, dict) else None
        pay_oid = payment.get("order_id") if isinstance(payment, dict) else None
    except Exception:
        pay_pid = pay_oid = None
    if pay_pid or pay_oid:
        q = {"$or": []}
        if pay_pid:
            q["$or"].append({"payment.payment_id": pay_pid})
        if pay_oid:
            q["$or"].append({"payment.order_id": pay_oid})
        if q["$or"]:
            existing = await db["bookings"].find_one(q)
            if existing:
                out = serialize_doc(existing)
                if response is not None:
                    response.status_code = 200
                return {"id": out.get("id"), "reference": out.get("reference"), "status": out.get("status"), "allocated_cottages": out.get("allocated_cottages"), "price_breakdown": out.get("price_breakdown")}

    selected = data.get("selected_cottages") or []

    busy_ids = await db["bookings"].distinct("allocated_cottages", {
        "status": {"$in": ["confirmed", "pending"]},
        "check_in": {"$lt": e},
        "check_out": {"$gt": s}
    })
    busy_ids = [b for b in busy_ids if b]

    allocated = []
    if selected:
        # deterministic expansion: treat each unique selected id and a count of requested rooms
        counts = Counter(selected)
        busy_ids_str = [str(b) for b in busy_ids]
        # keep track of room ids we've allocated in this request to avoid duplicates
        allocated_strs = set()

        for sid, qty in counts.items():
            # Attempt to resolve sid as a room id first
            resolved_rooms = []

            # Try ObjectId conversion -> room
            try:
                oid_try = ObjectId(sid)
                room_doc = await db["rooms"].find_one({"_id": oid_try})
                if room_doc:
                    # if qty >1 but only one physical room id provided, it's invalid
                    if qty > 1:
                        raise HTTPException(status_code=400, detail=f"Requested {qty} rooms but {sid} is a single room id")
                    resolved_rooms = [room_doc]
            except Exception:
                # ignore conversion errors
                resolved_rooms = []

            # If not a room, try matching by room fields (accommodation_id/id/_id string)
            if not resolved_rooms:
                try:
                    r = await db["rooms"].find_one({"$or": [{"accommodation_id": sid}, {"id": sid}, {"_id": sid}]})
                    if r:
                        if qty > 1:
                            raise HTTPException(status_code=400, detail=f"Requested {qty} rooms but {sid} resolves to a single room")
                        resolved_rooms = [r]
                except Exception:
                    resolved_rooms = []

            # If still not a specific room, treat sid as an accommodation id/slug and expand to `qty` room docs
            if not resolved_rooms:
                try:
                    acc = await db["accommodations"].find_one({"$or": [{"id": sid}, {"_id": sid}, {"slug": sid}]})
                except Exception:
                    acc = None
                if not acc:
                    logger.warning(f"create_booking: couldn't resolve selected id {sid}")
                    raise HTTPException(status_code=400, detail=f"Cottage {sid} not found")

                # Query rooms for this accommodation deterministically by _id (stable ordering)
                try:
                    rooms_cursor = db["rooms"].find({"$or": [{"accommodation_id": acc.get("_id")}, {"accommodation_id": str(acc.get("_id"))}] }).sort([("_id", 1)])
                    rooms = await rooms_cursor.to_list(length=None)
                except Exception:
                    rooms = []

                # Filter out busy rooms and already allocated ones
                available = [r for r in rooms if str(r.get("_id")) not in busy_ids_str and str(r.get("_id")) not in allocated_strs]
                if len(available) < qty:
                    raise HTTPException(status_code=400, detail=f"Not enough available rooms in accommodation {sid} for requested quantity")
                resolved_rooms = available[:qty]

            # Now convert resolved_rooms to ObjectIds and check overlaps, append to allocated
            for rdoc in resolved_rooms:
                oid_final = rdoc.get("_id")
                try:
                    if not isinstance(oid_final, ObjectId):
                        oid_final = ObjectId(str(oid_final))
                except Exception:
                    pass

                # check overlapping bookings again for safety
                overlapping = await db["bookings"].find_one({
                    "allocated_cottages": oid_final,
                    "status": {"$in": ["confirmed", "pending"]},
                    "check_in": {"$lt": e},
                    "check_out": {"$gt": s}
                })
                if overlapping:
                    resolved_id = str(oid_final) if oid_final is not None else sid
                    logger.warning(f"create_booking: selected cottage {sid} (resolved {resolved_id}) is overlapping")
                    raise HTTPException(status_code=400, detail=f"Cottage {sid} not available for selected dates")

                allocated.append(oid_final)
                allocated_strs.add(str(oid_final))


@router.get("/_debug/room/{room_id}")
async def debug_room(request: Request, room_id: str):
    """Debug helper: attempt to resolve a room id against the `rooms` collection.
    This tries ObjectId conversion and also a string-match fallback so you can
    verify which form of id your frontend is sending and whether the DB has
    the expected document.
    """
    db = get_db_or_503(request)
    tried = []
    # try as ObjectId
    try:
        oid = ObjectId(room_id)
        tried.append({"as_object_id": str(oid)})
        doc = await db["rooms"].find_one({"_id": oid})
        if doc:
            return {"found": True, "method": "object_id", "doc": serialize_doc(doc)}
    except Exception:
        tried.append({"as_object_id": None})

    # try exact string match on accommodation_id or id fields
    doc = await db["rooms"].find_one({"$or": [{"accommodation_id": room_id}, {"id": room_id}, {"_id": room_id}]})
    if doc:
        return {"found": True, "method": "string_match", "doc": serialize_doc(doc)}

    # try searching by name fragment
    docs = await db["rooms"].find({"name": {"$regex": room_id, "$options": "i"}}).to_list(length=5)
    return {"found": False, "tried": tried, "matches": [serialize_doc(d) for d in docs]}


@router.get("/rooms/name-debug/{room_name}")
async def rooms_name_debug(request: Request, room_name: str):
    """Debug helper: return room document using several lookup strategies (name/slug/id/_id/accommodation)."""
    db = get_db_or_503(request)
    # try direct id field
    try:
        doc = await db["rooms"].find_one({"id": room_name})
        if doc:
            return {"found": True, "method": "id", "doc": serialize_doc(doc)}
    except Exception:
        pass
    # try slug
    try:
        doc = await db["rooms"].find_one({"slug": room_name})
        if doc:
            return {"found": True, "method": "slug", "doc": serialize_doc(doc)}
    except Exception:
        pass
    # try name regex
    try:
        doc = await db["rooms"].find_one({"name": {"$regex": f"^{re.escape(room_name)}$", "$options": "i"}})
        if doc:
            return {"found": True, "method": "name", "doc": serialize_doc(doc)}
    except Exception:
        pass
    # try accommodation lookup
    try:
        acc = await db["accommodations"].find_one({"$or": [{"slug": room_name}, {"id": room_name}, {"name": {"$regex": f"^{re.escape(room_name)}$", "$options": "i"}}]})
    except Exception:
        acc = None
    if acc:
        try:
            rooms = await db["rooms"].find({"$or": [{"accommodation_id": acc.get("_id")}, {"accommodation_id": str(acc.get("_id"))}]}).to_list(length=None)
            return {"found": True, "method": "accommodation", "acc": serialize_doc(acc), "rooms": [serialize_doc(r) for r in rooms]}
        except Exception:
            pass
    return {"found": False}


@router.get("/_debug/counts")
async def debug_counts(request: Request):
    db = get_db_or_503(request)
    try:
        acc = await db["accommodations"].count_documents({})
        rooms = await db["rooms"].count_documents({})
        bookings = await db["bookings"].count_documents({})
        names = await db.list_collection_names()
        return {"ok": True, "counts": {"accommodations": acc, "rooms": rooms, "bookings": bookings}, "collections": names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not allocated:
        q = {"available": True}
        if busy_ids:
            q["_id"] = {"$nin": busy_ids}
        candidates = await db["rooms"].find(q).to_list(length=None)
        allow_extra = bool(data.get("allow_extra_beds", False) or data.get("extra_bedding", False))
        prefs = data.get("preferred_room_types", None)
        allocated = allocate_rooms(candidates, guests, allow_extra_beds=allow_extra, preferred_room_types=prefs, max_k=4)
        if not allocated:
            raise HTTPException(status_code=400, detail="Not enough cottages available for requested guests/dates")

    doc = {
        "reference": gen_reference(),
        "guest_name": data.get("guest_name"),
        "guest_email": email,
        "guest_phone": data.get("guest_phone"),
        "guests": guests,
        "selected_cottages": selected,
        "allocated_cottages": allocated,
        "payment": data.get("payment"),
        "extra_bedding": bool(data.get("allow_extra_beds", False) or data.get("extra_bedding", False)),
        "check_in": s,
        "check_out": e,
        "nights": (e - s).days,
        "price_breakdown": {},
        "status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    nights = doc.get("nights", 0) or 0
    room_docs = []
    if allocated:
        room_docs = await db["rooms"].find({"_id": {"$in": allocated}}).to_list(length=None)
    rooms_subtotal = 0.0
    per_room = []
    for r in room_docs:
        price = r.get("price_per_night") or r.get("pricePerNight") or r.get("price") or 0
        rooms_subtotal += float(price) * max(int(nights), 1)
        per_room.append({"room_id": str(r.get("_id")), "price_per_night": price})

    # Handle selected wellness programs (optional) and include in pricing
    programs_subtotal = 0.0
    program_items = []
    sel_programs = data.get("selected_programs") or []
    if sel_programs:
        for pid in sel_programs:
            prog_doc = None
            try:
                oid = ObjectId(pid)
                prog_doc = await db["wellnessPrograms"].find_one({"_id": oid})
            except Exception:
                prog_doc = None
            if not prog_doc:
                # try string match fields in wellnessPrograms
                prog_doc = await db["wellnessPrograms"].find_one({"$or": [{"id": pid}, {"_id": pid}]})
            if not prog_doc:
                prog_doc = await db["programs"].find_one({"$or": [{"_id": pid}, {"id": pid}]})
            if not prog_doc:
                # not found; skip silently to avoid blocking booking creation
                continue
            p = serialize_doc(prog_doc)
            p_price = p.get("price") or p.get("price_inr") or p.get("cost") or 0
            try:
                p_price_val = int(float(p_price))
            except Exception:
                p_price_val = 0
            programs_subtotal += p_price_val
            program_items.append({"program_id": str(p.get("id") or p.get("_id") or pid), "title": p.get("title") or p.get("name"), "price": p_price_val})

    combined_subtotal = rooms_subtotal + programs_subtotal
    tax = round(combined_subtotal * 0.18, 2)
    total = round(combined_subtotal + tax, 2)
    doc["price_breakdown"] = {
        "rooms_subtotal": round(rooms_subtotal, 2),
        "programs_subtotal": round(programs_subtotal, 2),
        "tax": tax,
        "total": total,
        "per_room": per_room,
        "programs": program_items,
    }

    res = await db["bookings"].insert_one(doc)
    created = await db["bookings"].find_one({"_id": res.inserted_id})

    out = serialize_doc(created)
    try:
        from resort_backend.routes.events import publish_event
        publish_event({"event": "bookings.created", "payload": {"id": out.get("id"), "reference": out.get("reference"), "status": out.get("status")}})
    except Exception:
        pass

    return {"id": out.get("id"), "reference": out.get("reference"), "status": out.get("status"), "allocated_cottages": out.get("allocated_cottages"), "price_breakdown": out.get("price_breakdown")}


@router.get("/debug/db-info")
async def debug_db_info(request: Request, sample_col: Optional[str] = None, limit: int = 5):
    """Return visible collection names and optional sample documents for a given collection.

    Example: `/api/debug/db-info?sample_col=wellnessPrograms&limit=3`
    """
    db = get_db_or_503(request)
    try:
        names = await db.list_collection_names()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to list collections")
    out = {"collections": names}
    if sample_col:
        if sample_col not in names:
            raise HTTPException(status_code=404, detail=f"Collection {sample_col} not found")
        try:
            docs = await db[sample_col].find().limit(limit).to_list(length=limit)
            out["sample"] = [serialize_doc(d) for d in docs]
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to fetch sample documents")
    return out
