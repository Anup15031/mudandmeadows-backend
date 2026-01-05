
from fastapi import APIRouter, HTTPException, Request
from resort_backend.utils import get_db_or_503, serialize_doc
from pydantic import BaseModel
from typing import Optional
from bson import ObjectId

router = APIRouter(tags=["dining"])


# Pydantic model for menu item
class MenuItem(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    image: Optional[str] = None  # main image (for backward compatibility)
    images: Optional[list[str]] = None  # multiple images
    tags: Optional[list[str]] = None  # e.g. "spicy", "vegan"
    amenities: Optional[list[str]] = None  # e.g. "Gluten Free", "Organic"
    available: Optional[bool] = True

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    image: Optional[str] = None
    images: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    amenities: Optional[list[str]] = None
    available: Optional[bool] = None

@router.get("/dining/all")
async def get_dining(request: Request):
    """
    Returns all menu items from the 'menu' collection in MongoDB.
    """
    db = get_db_or_503(request)
    try:
        items = await db["menu"].find().to_list(None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    if not items:
        raise HTTPException(status_code=404, detail="No menu items found in 'menu' collection.")
    return [serialize_doc(i) for i in items]

@router.post("/dining", status_code=201)
async def create_menu_item(request: Request, item: MenuItem):
    db = get_db_or_503(request)
    try:
        result = await db["menu"].insert_one(item.dict())
        new_item = await db["menu"].find_one({"_id": result.inserted_id})
        return serialize_doc(new_item)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/dining/{item_id}")
async def update_menu_item(request: Request, item_id: str, item: MenuItemUpdate):
    db = get_db_or_503(request)
    try:
        update_data = {k: v for k, v in item.dict().items() if v is not None}
        result = await db["menu"].update_one({"_id": ObjectId(item_id)}, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Menu item not found.")
        updated_item = await db["menu"].find_one({"_id": ObjectId(item_id)})
        return serialize_doc(updated_item)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/dining/{item_id}", status_code=204)
async def delete_menu_item(request: Request, item_id: str):
    db = get_db_or_503(request)
    try:
        result = await db["menu"].delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Menu item not found.")
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
