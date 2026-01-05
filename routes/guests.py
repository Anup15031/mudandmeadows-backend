from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from datetime import datetime
from resort_backend.utils import get_db_or_503, serialize_doc, hash_password

router = APIRouter(tags=["guests"])

class GuestProfile(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str
    phone: str | None = None

@router.post("/")
async def create_guest(request: Request, body: GuestProfile):
    db = get_db_or_503(request)
    # upsert by email
    existing = await db['guests'].find_one({'email': body.email})
    doc = {
        'email': body.email,
        'first_name': body.first_name,
        'last_name': body.last_name,
        'phone': body.phone,
        'created_at': datetime.utcnow(),
    }
    if existing:
        await db['guests'].update_one({'_id': existing['_id']}, {'$set': doc})
        guest = await db['guests'].find_one({'_id': existing['_id']})
    else:
        res = await db['guests'].insert_one(doc)
        guest = await db['guests'].find_one({'_id': res.inserted_id})
    return serialize_doc(guest)

@router.get('/by-email/{email}')
async def get_guest_by_email(request: Request, email: str):
    db = get_db_or_503(request)
    g = await db['guests'].find_one({'email': email})
    if not g:
        raise HTTPException(status_code=404, detail='Guest not found')
    return serialize_doc(g)
