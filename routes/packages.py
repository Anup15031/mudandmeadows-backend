from fastapi import APIRouter, HTTPException, Request
from resort_backend.models import Package
from bson import ObjectId
from datetime import datetime
from resort_backend.utils import get_db_or_503, serialize_doc

router = APIRouter(tags=["packages"])

@router.get("/")
async def get_all_packages(request: Request):
    """Get all packages"""
    db = get_db_or_503(request)
    packages = await db["packages"].find().to_list(None)
    return [serialize_doc(pkg) for pkg in packages]

@router.get("/{package_id}")
async def get_package(request: Request, package_id: str):
    """Get a specific package by ID"""
    db = get_db_or_503(request)
    try:
        package = await db["packages"].find_one({"_id": ObjectId(package_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid package id")
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    return serialize_doc(package)

@router.post("/")
async def create_package(request: Request, package: Package):
    """Create a new package"""
    db = get_db_or_503(request)
    pkg_dict = package.dict()
    pkg_dict["created_at"] = datetime.utcnow()
    result = await db["packages"].insert_one(pkg_dict)
    created = await db["packages"].find_one({"_id": result.inserted_id})
    return serialize_doc(created)

@router.put("/{package_id}")
async def update_package(request: Request, package_id: str, package: Package):
    """Update a package"""
    db = get_db_or_503(request)
    try:
        result = await db["packages"].update_one(
            {"_id": ObjectId(package_id)},
            {"$set": package.dict()}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid package id")
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Package not found")
    updated = await db["packages"].find_one({"_id": ObjectId(package_id)})
    return serialize_doc(updated)

@router.delete("/{package_id}")
async def delete_package(request: Request, package_id: str):
    """Delete a package"""
    db = get_db_or_503(request)
    try:
        result = await db["packages"].delete_one({"_id": ObjectId(package_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid package id")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Package not found")
    return {"message": "Package deleted successfully"}
