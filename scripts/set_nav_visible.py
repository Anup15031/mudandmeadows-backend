#!/usr/bin/env python3
"""
Set `is_visible: true` for common navigation items in the `navigation` collection.

Usage:
  python scripts\set_nav_visible.py            # runs default safe list
  python scripts\set_nav_visible.py --labels Cottages Programs
  python scripts\set_nav_visible.py --dry-run  # show what would change

The script reads `MONGODB_URL` and `DATABASE_NAME` from environment (or .env if present).
It uses `pymongo` for a synchronous update.
"""
import os
import argparse
from pymongo import MongoClient
from dotenv import load_dotenv


load_dotenv()


DEFAULT_LABELS = [
    "Cottages",
    "Programs",
    "Dining",
    "Gallery",
    "Packages",
    "Contact",
    "Wellness Programs",
    "Resort Activities",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", nargs="*", help="Labels (or names) of nav items to mark visible")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without writing")
    args = parser.parse_args()

    mongo_url = os.getenv("MONGODB_URL")
    db_name = os.getenv("DATABASE_NAME", "resort_db")
    if not mongo_url:
        print("MONGODB_URL not set in environment; aborting")
        return

    labels = args.labels if args.labels else DEFAULT_LABELS

    client = MongoClient(mongo_url)
    db = client[db_name]
    coll = db["navigation"]

    print(f"Using DB {db_name}; will target labels/names: {labels}")
    query = {"$or": [{"label": {"$in": labels}}, {"name": {"$in": labels}}]}
    docs = list(coll.find(query))
    if not docs:
        print("No matching navigation documents found for provided labels.")
        return

    print(f"Found {len(docs)} document(s) matching query.")
    for d in docs:
        print("-", d.get("_id"), d.get("label") or d.get("name"), "current is_visible=", d.get("is_visible"))

    if args.dry_run:
        print("Dry run: no changes made")
        return

    res = coll.update_many(query, {"$set": {"is_visible": True}})
    print(f"Updated {res.modified_count} document(s).")


if __name__ == "__main__":
    main()
