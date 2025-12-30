from resort_backend.routes import cottages
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
from resort_backend.routes import accommodations, packages, experiences, wellness, bookings, home, menu_items, gallery, api_compat, internal_status, navigation, api_site
from resort_backend.routes import events, extra_beds, programs
from resort_backend.routes import razorpay
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
import json
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load .env into the process environment so runtime env vars (e.g. API_KEY) are available
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger("resort_backend")
    logger.info("LIFESPAN: Startup initiated")
    try:
        await connect_db()
        logger.info("LIFESPAN: connect_db() completed")
        # attach db handle to app.state for routes to access
        try:
            app.state.db = database.get_db()
            app.state.db_client = getattr(database, "client", None)
            logger.info("App startup: DB attached to app.state (db set: %s, client set: %s)", app.state.db is not None, app.state.db_client is not None)
            try:
                client = getattr(app.state, "db_client", None)
                if client is not None:
                    cmd = client.admin.command("ping")
                    if hasattr(cmd, "__await__"):
                        await cmd
                    else:
                        client.admin.command("ping")
                    logger.info("App startup: DB ping successful")
                    try:
                        db_handle = getattr(app.state, "db", None)
                        if db_handle is not None:
                            await db_handle.locks.delete_many({"expire_at": {"$lt": datetime.utcnow()}})
                            logger.info("Cleaned up stale locks on startup")
                    except Exception:
                        logger.exception("Failed to cleanup stale locks on startup")
            except Exception:
                logger.exception("App startup: DB ping failed")
            if getattr(app.state, "db", None) is None or getattr(app.state, "db_client", None) is None:
                try:
                    import motor.motor_asyncio
                    from os import getenv
                    MONGODB_URL = getenv("MONGODB_URL")
                    from resort_backend.database import DATABASE_NAME
                    if MONGODB_URL:
                        logger.info("Attempting fallback DB client creation using MONGODB_URL from environment")
                        fb_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
                        try:
                            cmd = fb_client.admin.command("ping")
                            if hasattr(cmd, "__await__"):
                                await cmd
                            else:
                                fb_client.admin.command("ping")
                            app.state.db_client = fb_client
                            app.state.db = fb_client[DATABASE_NAME]
                            logger.info("Fallback DB client created and ping successful")
                        except Exception:
                            logger.exception("Fallback DB ping failed")
                except Exception:
                    logger.exception("Fallback DB client creation failed")
        except Exception:
            logger.exception("Error attaching DB to app.state (inner)")
    except Exception as e:
        logger.exception(f"LIFESPAN: Startup failed: {e}")
    logger.info("LIFESPAN: Startup complete, yielding to app")
    yield
    logger.info("LIFESPAN: Shutdown initiated")
    try:
        await close_db()
        logger.info("LIFESPAN: close_db() completed")
    except Exception as e:
        logger.exception(f"LIFESPAN: Shutdown failed: {e}")
    logger.info("LIFESPAN: Shutdown complete")

app = FastAPI(
    title="Resort Booking API",
    description="API documentation for Resort Booking backend.",
    version="1.0.0",
    docs_url="/docs",           # Swagger UI
    redoc_url="/redoc",         # ReDoc UI
    openapi_url="/openapi.json" # OpenAPI schema
)

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
    mongo_url = "mongodb://localhost:27017"
    db_name = "your_database_name"  # <-- set your actual DB name here
    client = AsyncIOMotorClient(mongo_url)
    app.state.db_client = client
    app.state.db = client[db_name]

@app.on_event("shutdown")
async def shutdown_db_client():
    client = getattr(app.state, "db_client", None)
    if client:
        client.close()

# Include routers
# Also include navigation router under /api for backwards compatibility with some clients
# Include gallery under /api for compatibility with clients expecting /api/gallery
# Expose extra beds under /api for frontend compatibility
app.include_router(cottages.router, prefix="/api")
app.include_router(home.router, prefix="/api")
app.include_router(accommodations.router, prefix="/api")
app.include_router(packages.router, prefix="/api")
app.include_router(experiences.router, prefix="/api")
app.include_router(wellness.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(api_compat.router, prefix="/api")
app.include_router(api_site.router, prefix="/api")
app.include_router(menu_items.router, prefix="/api")
app.include_router(gallery.router, prefix="/api")
app.include_router(navigation.router, prefix="/api")
app.include_router(internal_status.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(extra_beds.router, prefix="/api")
app.include_router(programs.router, prefix="/api")
app.include_router(razorpay.router, prefix="/api")
app.include_router(api_site.router)
# Authentication routes
from resort_backend.routes import auth
app.include_router(auth.router)
from resort_backend.routes import guests
app.include_router(guests.router)

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
