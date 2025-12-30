from fastapi import Request, HTTPException
from typing import Any, Dict
import logging
from bson import ObjectId
from datetime import datetime, date

logger = logging.getLogger("resort_backend.utils")


def get_db_or_503(request: Request):
    db = getattr(request.app.state, "db", None)
    if db is None:
        logger.error("Database not initialized when handling request %s", request.url.path)
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db


def _serialize_value(v: Any):
    """Recursively convert BSON types (ObjectId, datetime) to JSON-safe values."""
    if v is None:
        return None
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _serialize_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_serialize_value(x) for x in v]
    # primitive types (int, float, str, bool) are JSON-safe
    return v


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize a MongoDB document to JSON-safe dict. Converts `_id` to `id` and
    recursively converts ObjectId and datetime values.
    """
    if doc is None:
        return doc
    out = dict(doc)
    _id = out.pop("_id", None)
    try:
        if _id is not None:
            out["id"] = str(_id)
    except Exception:
        out["id"] = str(_id)
    # Recursively convert values
    for k, v in list(out.items()):
        out[k] = _serialize_value(v)
    return out


def hash_password(password: str) -> str:
    # lightweight PBKDF2 password hashing to avoid extra deps
    import hashlib, os, binascii
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return binascii.hexlify(salt).decode() + '$' + binascii.hexlify(dk).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        import hashlib, binascii
        salt_hex, dk_hex = stored.split('$', 1)
        salt = binascii.unhexlify(salt_hex)
        dk = binascii.unhexlify(dk_hex)
        new_dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return binascii.hexlify(new_dk).decode() == binascii.hexlify(dk).decode()
    except Exception:
        return False
