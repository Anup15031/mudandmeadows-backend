"""
Script to mark expected public navigation items as visible.
Run from the repo root (resort_backend):

python scripts/ensure_navigation_public.py

This script connects to the database using the existing database module's
connection helper and updates navigation documents by name to set is_visible=True.
"""
import asyncio
from os import getenv

async def main():
    try:
        # Import lazily so this script reuses the project's database connection helpers
        import database
        from database import connect_db, get_db, close_db
    except Exception as e:
        print("Failed to import database helpers:", e)
        return

    await connect_db()
    db = get_db()
    if db is None:
        print("Database not available. Ensure MONGODB_URL is set and reachable.")
        await close_db()
        return

    targets = [
        {"name": "Cottages", "aliases": ["cottages", "Accommodations"]},
        {"name": "Programs", "aliases": ["programs"]},
        {"name": "Dining", "aliases": ["dining"]},
        {"name": "Gallery", "aliases": ["gallery"]},
        {"name": "Packages", "aliases": ["packages"]},
        {"name": "Contact", "aliases": ["contact"]},
    ]

    updated = 0
    for t in targets:
        names = [t["name"]] + t.get("aliases", [])
        for nm in names:
            res = await db["navigation"].update_many({"$or": [{"name": nm}, {"label": nm}, {"href": nm}, {"url": nm}]}, {"$set": {"is_visible": True}})
            if res.modified_count:
                print(f"Set is_visible=True for items matching '{nm}' -> {res.modified_count} updated")
                updated += res.modified_count

    if updated == 0:
        print("No navigation items updated. You may need to insert documents or adjust matching criteria.")
    else:
        print(f"Updated {updated} navigation documents to be visible.")

    await close_db()

if __name__ == '__main__':
    asyncio.run(main())
