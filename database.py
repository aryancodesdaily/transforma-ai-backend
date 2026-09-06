from pymongo import MongoClient
from config import MONGODB_URI

if not MONGODB_URI:
    raise ValueError("MONGODB_URI is missing from .env")

client = MongoClient(MONGODB_URI)

db = client["transforma_db"]

transformations_collection = db["transformations"]
from datetime import datetime, timezone

from datetime import datetime, timezone


def save_transformation(
    input_hash: str,
    output_hash: str
):
    previous_record = transformations_collection.find_one(
        sort=[("timestamp", -1)]
    )

    previous_output_hash = (
        previous_record["output_hash"]
        if previous_record
        else None
    )

    record = {
        "input_hash": input_hash,
        "output_hash": output_hash,
        "previous_output_hash": previous_output_hash,
        "timestamp": datetime.now(timezone.utc),
    }

    result = transformations_collection.insert_one(record)

    return result.inserted_id