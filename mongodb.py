from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from config import MONGODB_URI


if not MONGODB_URI:
    raise ValueError("MONGODB_URI is missing from .env")


client = MongoClient(MONGODB_URI)

try:
    client.admin.command("ping")
    print("MongoDB connected successfully.")
except ConnectionFailure as error:
    print(f"MongoDB connection failed: {error}")
    raise


db = client["transforma_ai"]

transformations_collection = db["transformations"]

# Very important:
# One document must exist for each unique input hash.
transformations_collection.create_index(
    "input_hash",
    unique=True
)