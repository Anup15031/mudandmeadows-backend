from resort_backend.routes import cottages
from resort_backend.routes import bookings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from contextlib import asynccontextmanager
import logging
from dotenv import load_dotenv
import os
from datetime import datetime
from resort_backend.routes import api_site

from pathlib import Path
# Ensure .env is loaded before importing route modules so route-level
# module-scope env reads (e.g. INTERNAL_API_KEY) pick up values.
env_paths = [
    Path(__file__).parent / ".env",
    Path(__file__).parent.parent / ".env"
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break
import resort_backend.database as database
from resort_backend.database import connect_db, close_db, get_db
from resort_backend.routes import accommodations, packages, experiences, wellness, bookings, home, gallery, api_compat, internal_status, navigation, api_site
from resort_backend.routes import events, extra_beds, programs
from resort_backend.routes import razorpay
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
import json
import os
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()  # Ensure .env is loaded

app = FastAPI(
    title="Resort Booking API",
    description="API documentation for Resort Booking backend.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

@app.on_event("startup")
async def startup_db_client():
    # Always use the .env values for MongoDB connection
    mongo_url = os.getenv("MONGODB_URL")
    db_name = os.getenv("DATABASE_NAME")
    if not mongo_url or not db_name:
        raise RuntimeError("MONGODB_URL and DATABASE_NAME must be set in .env")
    try:
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
        await client.server_info()
        app.state.db_client = client
        app.state.db = client[db_name]
    except Exception as e:
        import sys
        print(f"Could not connect to MongoDB at {mongo_url}: {e}", file=sys.stderr)
        raise RuntimeError("MongoDB connection failed. Is the database URL correct and MongoDB accessible?")

@app.on_event("shutdown")
async def shutdown_db_client():
    client = getattr(app.state, "db_client", None)
    if client:
        client.close()

# Configure rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Prefer explicit frontend origin to allow credentials (cookies)
        os.environ.get('FRONTEND_URL', 'http://localhost:3000'),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Initialization ---
@app.on_event("startup")
async def startup_db_client():
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name = os.getenv("DATABASE_NAME", "test")
    try:
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
        # Try to force a connection on startup to fail fast if MongoDB is not running
        await client.server_info()
        app.state.db_client = client
        app.state.db = client[db_name]
    except Exception as e:
        import sys
        print(f"Could not connect to MongoDB at {mongo_url}: {e}", file=sys.stderr)
        # Optionally: raise or exit to prevent app from running without DB
        raise RuntimeError("MongoDB connection failed. Is the database URL correct and MongoDB accessible?")

@app.on_event("shutdown")
async def shutdown_db_client():
    client = getattr(app.state, "db_client", None)
    if client:
        client.close()

# Include routers
# Also include navigation router under /api for backwards compatibility with some clients
# Include gallery under /api for compatibility with clients expecting /api/gallery
# Expose extra beds under /api for frontend compatibility

app.include_router(cottages.router, prefix="/api/cottages")
app.include_router(home.router, prefix="/api/home")
app.include_router(accommodations.router, prefix="/api/accommodations")
app.include_router(packages.router, prefix="/api/packages")
app.include_router(experiences.router, prefix="/api/experiences")
app.include_router(wellness.router, prefix="/api/wellness")
app.include_router(bookings.router, prefix="/api/bookings")
app.include_router(api_compat.router, prefix="/api/api_compat")
app.include_router(api_site.router, prefix="/api/api_site")
app.include_router(gallery.router, prefix="/api/gallery")
app.include_router(navigation.router, prefix="/api/navigation")
app.include_router(internal_status.router, prefix="/api/internal_status")
app.include_router(events.router, prefix="/api/events")
app.include_router(extra_beds.router, prefix="/api/extra_beds")
app.include_router(programs.router, prefix="/api/programs")
app.include_router(razorpay.router, prefix="/api/razorpay")
from resort_backend.routes import reviews
app.include_router(reviews.router, prefix="/api/reviews")
# Authentication routes
from resort_backend.routes import auth
app.include_router(auth.router, prefix="/api/auth")
from resort_backend.routes import guests
app.include_router(guests.router, prefix="/api/guests")
from resort_backend.routes.dining import router as dining_router
app.include_router(dining_router, prefix="/api/dining")
from resort_backend.routes.contact import router as contact_router
app.include_router(contact_router, prefix="/api/contact")

# Serve uploaded files from /uploads
uploads_path = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_path, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

@app.get("/")
async def root():
    return {
        "message": "Welcome to Resort Backend API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/site/site-config.js")
async def site_config_js_root():
    # Provide a tiny JS snippet used by the frontend dev toolbar
    config = {"apiBase": "/api", "siteName": "Resort"}
    body = "window.__SITE_CONFIG__ = " + json.dumps(config) + ";"
    return Response(content=body, media_type="application/javascript")


# Compatibility route: some frontends request the site-config under /api
@app.get("/api/site/site-config.js")
async def site_config_js_api():
    config = {"apiBase": "/api", "siteName": "Resort"}
    body = "window.__SITE_CONFIG__ = " + json.dumps(config) + ";"
    return Response(content=body, media_type="application/javascript")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/debug/routes")
async def debug_routes():
    # Return list of registered routes (path + methods) for debugging
    out = []
    for r in app.routes:
        methods = []
        try:
            methods = list(getattr(r, "methods", []) or [])
        except Exception:
            pass
        out.append({"path": getattr(r, "path", str(r)), "methods": methods})
    return out

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
