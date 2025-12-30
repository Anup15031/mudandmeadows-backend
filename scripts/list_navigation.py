#!/usr/bin/env python3
"""List navigation documents from the configured MongoDB.

Reads `MONGODB_URL` and `DATABASE_NAME` from the environment (or .env).
Prints `_id`, `name`, `label`, `is_visible`, `href`/`url`, and `order` for each document.
"""
import os
import argparse
import json
from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--skip", type=int, default=0)
    p.add_argument("--filter", choices=["all", "visible", "hidden"], default="all")
    args = p.parse_args()

    mongo_url = os.getenv("MONGODB_URL")
    db_name = os.getenv("DATABASE_NAME", "resort_db")
    if not mongo_url:
        print("MONGODB_URL not set in environment; aborting")
        return

    try:
        client = MongoClient(mongo_url)
        db = client[db_name]
    except Exception as e:
        print("Failed to connect to MongoDB:", e)
        return

    coll = db["navigation"]
    q = {}
    if args.filter == "visible":
        q["is_visible"] = True
    elif args.filter == "hidden":
        q["is_visible"] = False

    try:
        total = coll.count_documents(q)
    except Exception as e:
        print("Failed to count navigation documents:", e)
        return

    print(f"DB={db_name} navigation documents matching {q!r}: {total}")
    try:
        cursor = coll.find(q).skip(args.skip).limit(args.limit)
        for d in cursor:
            out = {
                "_id": str(d.get("_id")),
                "name": d.get("name"),
                "label": d.get("label"),
                "is_visible": d.get("is_visible"),
                "href": d.get("href") or d.get("url"),
                "order": d.get("order"),
            }
            print(json.dumps(out, ensure_ascii=False))
    except Exception as e:
        print("Failed to read navigation documents:", e)


if __name__ == "__main__":
    main()
