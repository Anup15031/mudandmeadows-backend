from fastapi import APIRouter, HTTPException, Request
from bson import ObjectId
from datetime import datetime
from resort_backend.utils import get_db_or_503, serialize_doc

router = APIRouter(prefix="/menu-items", tags=["menu-items"])

# Module-level variable to store database connection
_db = None

def set_db(database):
    """Set the database connection for this module"""
    global _db
    _db = database

@router.get("/")
async def get_all_menu_items(request: Request):
    """Get all menu items"""
    db = get_db_or_503(request)
    try:
        menu_items = await db["menu_items"].find().to_list(None)
        return [serialize_doc(item) for item in menu_items]
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch menu items")

@router.get("/{menu_item_id}")
async def get_menu_item(request: Request, menu_item_id: str):
    """Get a specific menu item by ID"""
    db = get_db_or_503(request)
    try:
        menu_item = await db["menu_items"].find_one({"_id": ObjectId(menu_item_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid menu item id")
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return serialize_doc(menu_item)

@router.post("/")
async def create_menu_item(request: Request, menu_item: dict):
    """Create a new menu item"""
    db = get_db_or_503(request)
    item_dict = menu_item
    item_dict["created_at"] = datetime.utcnow()
    result = await db["menu_items"].insert_one(item_dict)
    created = await db["menu_items"].find_one({"_id": result.inserted_id})
    return serialize_doc(created)

@router.put("/{menu_item_id}")
async def update_menu_item(request: Request, menu_item_id: str, menu_item: dict):
    """Update a menu item"""
    db = get_db_or_503(request)
    try:
        result = await db["menu_items"].update_one(
            {"_id": ObjectId(menu_item_id)},
            {"$set": menu_item}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid menu item id")
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Menu item not found")
    updated = await db["menu_items"].find_one({"_id": ObjectId(menu_item_id)})
    return serialize_doc(updated)

@router.delete("/{menu_item_id}")
async def delete_menu_item(request: Request, menu_item_id: str):
    """Delete a menu item"""
    db = get_db_or_503(request)
    try:
        result = await db["menu_items"].delete_one({"_id": ObjectId(menu_item_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid menu item id")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return {"message": "Menu item deleted successfully"}
