from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime, timedelta
from uuid import uuid4
import jwt
from resort_backend.utils import get_db_or_503, hash_password, verify_password, serialize_doc
import os
from urllib.parse import urlencode
import httpx

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
JWT_ALGO = "HS256"
JWT_EXP_MIN = int(os.environ.get("JWT_EXP_MIN", "60"))

class RegisterRequest(BaseModel):
    email: str
    password: str
    first_name: str | None = None
    last_name: str | None = None

class LoginRequest(BaseModel):
    email: str
    password: str


def create_token(user: dict) -> str:
    payload = {
        "sub": str(user.get("_id")),
        "email": user.get("email"),
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXP_MIN),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def _cookie_settings():
    secure = os.environ.get('FORCE_HTTPS', '0') in ('1', 'true', 'True')
    max_age = JWT_EXP_MIN * 60
    return {
        'httponly': True,
        'secure': secure,
        'samesite': 'lax',
        'max_age': max_age,
    }


# --- Google OAuth endpoints
@router.get('/oauth/google')
async def oauth_google(request: Request):
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    if not client_id:
        raise HTTPException(status_code=400, detail='Google OAuth not configured')
    backend_url = os.environ.get('BACKEND_URL', 'http://localhost:8080')
    redirect_uri = os.environ.get('GOOGLE_OAUTH_REDIRECT', f"{backend_url}/auth/oauth/google/callback")
    # create a short-lived signed state to mitigate CSRF
    state_payload = {
        'nonce': uuid4().hex,
        'ts': int(datetime.utcnow().timestamp()),
        'exp': int((datetime.utcnow() + timedelta(minutes=5)).timestamp()),
    }
    state = jwt.encode(state_payload, JWT_SECRET, algorithm=JWT_ALGO)
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'offline',
        'prompt': 'select_account consent',
    }
    url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(params)
    return RedirectResponse(url)


@router.get('/oauth/google/callback')
async def oauth_google_callback(request: Request, code: str | None = None, error: str | None = None, state: str | None = None):
    if error:
        raise HTTPException(status_code=400, detail=f'Google OAuth error: {error}')
    if not code:
        raise HTTPException(status_code=400, detail='Missing code from Google')

    # verify state
    if not state:
        raise HTTPException(status_code=400, detail='Missing state in OAuth response')
    try:
        decoded = jwt.decode(state, JWT_SECRET, algorithms=[JWT_ALGO])
        # optional: check exp claim handled by jwt.decode
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid or expired OAuth state')

    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    backend_url = os.environ.get('BACKEND_URL', 'http://localhost:8080')
    redirect_uri = os.environ.get('GOOGLE_OAUTH_REDIRECT', f"{backend_url}/auth/oauth/google/callback")
    if not (client_id and client_secret):
        raise HTTPException(status_code=400, detail='Google OAuth client not configured')

    token_url = 'https://oauth2.googleapis.com/token'
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data={
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        })
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail='Failed to exchange code with Google')
        token_data = resp.json()
        access_token = token_data.get('access_token')
        if not access_token:
            raise HTTPException(status_code=502, detail='No access token from Google')

        userinfo_resp = await client.get('https://openidconnect.googleapis.com/v1/userinfo', headers={'Authorization': f'Bearer {access_token}'})
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=502, detail='Failed to fetch user info from Google')
        info = userinfo_resp.json()

    db = get_db_or_503(request)
    email = info.get('email')
    if not email:
        raise HTTPException(status_code=400, detail='Google account has no email')

    existing = await db['users'].find_one({'email': email})
    if existing:
        user = existing
    else:
        # create a lightweight user record (no password)
        doc = {
            'email': email,
            'first_name': info.get('given_name'),
            'last_name': info.get('family_name'),
            'picture': info.get('picture'),
            'created_at': datetime.utcnow(),
            'oauth_provider': 'google',
            'oauth_sub': info.get('sub'),
        }
        res = await db['users'].insert_one(doc)
        user = await db['users'].find_one({'_id': res.inserted_id})

    token = create_token(user)
    frontend = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    redirect_to = f"{frontend}/auth/complete"
    resp = RedirectResponse(redirect_to)
    cs = _cookie_settings()
    resp.set_cookie(key='auth_token', value=token, httponly=cs['httponly'], secure=cs['secure'], samesite=cs['samesite'], max_age=cs['max_age'])
    return resp


def get_current_user(request: Request):
    # Support Authorization header Bearer token or auth_token cookie
    auth = request.headers.get("Authorization")
    token = None
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
    else:
        token = request.cookies.get('auth_token')
    if not token:
        raise HTTPException(status_code=401, detail="Missing credentials")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    db = get_db_or_503(request)
    from bson import ObjectId
    try:
        uid = ObjectId(payload.get("sub"))
    except Exception:
        uid = payload.get("sub")
    user = db["users"].find_one({"_id": uid}) if uid else None
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return serialize_doc(user)


@router.post("/register")
async def register(request: Request, body: RegisterRequest):
    db = get_db_or_503(request)
    existing = await db["users"].find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    hashed = hash_password(body.password)
    doc = {
        "email": body.email,
        "password_hash": hashed,
        "first_name": body.first_name,
        "last_name": body.last_name,
        "created_at": datetime.utcnow(),
    }
    res = await db["users"].insert_one(doc)
    user = await db["users"].find_one({"_id": res.inserted_id})
    token = create_token(user)
    out = serialize_doc(user)
    # set auth cookie and return user without token in body
    cs = _cookie_settings()
    resp = JSONResponse(content=out)
    resp.set_cookie(key='auth_token', value=token, httponly=cs['httponly'], secure=cs['secure'], samesite=cs['samesite'], max_age=cs['max_age'])
    return resp


@router.post("/login")
async def login(request: Request, body: LoginRequest):
    db = get_db_or_503(request)
    user = await db["users"].find_one({"email": body.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(body.password, user.get("password_hash")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user)
    out = serialize_doc(user)
    # set auth cookie and return user without token in body
    cs = _cookie_settings()
    resp = JSONResponse(content=out)
    resp.set_cookie(key='auth_token', value=token, httponly=cs['httponly'], secure=cs['secure'], samesite=cs['samesite'], max_age=cs['max_age'])
    return resp


@router.get("/me")
async def me(request: Request):
    user = get_current_user(request)
    return user
