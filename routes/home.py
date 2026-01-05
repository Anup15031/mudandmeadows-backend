from fastapi import APIRouter, Request
from resort_backend.models import HomePage
from resort_backend.utils import get_db_or_503, serialize_doc

router = APIRouter(tags=["home"])


@router.get("/")
async def get_home_page(request: Request):
    """Get home page data with featured items"""
    db = get_db_or_503(request)
    accommodations = await db["accommodations"].find().limit(3).to_list(3)
    packages = await db["packages"].find().limit(3).to_list(3)
    experiences = await db["experiences"].find().limit(3).to_list(3)

    return {
        "title": "Welcome to Paradise Resort",
        "description": "Experience luxury and wellness at our premium resort",
        "featured_accommodations": [serialize_doc(acc) for acc in accommodations],
        "featured_packages": [serialize_doc(pkg) for pkg in packages],
        "featured_experiences": [serialize_doc(exp) for exp in experiences],
    }

@router.get("/stats")
async def get_stats(request: Request):
    """Get resort statistics"""
    db = get_db_or_503(request)
    total_accommodations = await db["accommodations"].count_documents({})
    total_packages = await db["packages"].count_documents({})
    total_experiences = await db["experiences"].count_documents({})
    total_wellness = await db["wellness"].count_documents({})
    total_bookings = await db["bookings"].count_documents({})

    return {
        "total_accommodations": total_accommodations,
        "total_packages": total_packages,
        "total_experiences": total_experiences,
        "total_wellness_services": total_wellness,
        "total_bookings": total_bookings,
    }
