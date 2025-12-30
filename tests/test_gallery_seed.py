import os
from pymongo import MongoClient


def test_gallery_seed_exists():
    mongo_url = os.getenv("MONGODB_URL")
    db_name = os.getenv("DATABASE_NAME", "resort_db")
    assert mongo_url is not None, "MONGODB_URL must be set to run this test"
    client = MongoClient(mongo_url)
    db = client[db_name]
    count = db.gallery.count_documents({})
    client.close()
    assert count >= 1, "Expected at least 1 gallery document from seed"
