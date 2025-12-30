"""Ensure `menu` collection exists in the database.

Usage:
  set MONGODB_URL="..."
  set DATABASE_NAME=adivasi
  python scripts/ensure_menu_collection.py
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME", "adivasi")

SAMPLE = []
try:
    # try common import locations for SAMPLE_MENU_ITEMS
    try:
        # when invoked from project root
        from mongo_seed_menu import SAMPLE_MENU_ITEMS as SAMPLE_MENU_ITEMS
    except Exception:
        # when invoked as a package (scripts module)
        from ..mongo_seed_menu import SAMPLE_MENU_ITEMS as SAMPLE_MENU_ITEMS
    SAMPLE = SAMPLE_MENU_ITEMS
except Exception:
    SAMPLE = []

def ensure_menu():
    if not MONGODB_URL:
        print("MONGODB_URL not set")
        return
    client = MongoClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    try:
        menu_count = db.menu.count_documents({})
        if menu_count > 0:
            print(f"menu collection already has {menu_count} documents")
            return

        # try copying from menu_items
        try:
            items = list(db.menu_items.find().limit(1000))
            if items:
                for i in items:
                    i.pop("_id", None)
                db.menu.insert_many(items)
                print(f"Copied {len(items)} documents from menu_items -> menu")
                return
        except Exception:
            pass

        # fallback to SAMPLE data if present
        if SAMPLE:
            for i in SAMPLE:
                i.pop("_id", None)
            db.menu.insert_many(SAMPLE)
            print(f"Seeded {len(SAMPLE)} sample documents into menu collection")
            return

        print("No source data found to populate menu collection. Please add documents to `menu` or `menu_items` collection.")
    finally:
        client.close()

if __name__ == '__main__':
    ensure_menu()
