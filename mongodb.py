from pymongo import ASCENDING, MongoClient
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

# Flat, append-only chain of transformation records. Each transformation
# gets its own document (no grouping by input hash), linked to the
# previous record by prev_hash, so tampering with any past record
# breaks the chain from that point forward.
chain_records_collection = db["chain_records"]

# sequence must be unique and strictly increasing -> guarantees the
# chain has exactly one record per position, even under concurrent writes.
chain_records_collection.create_index(
    "sequence",
    unique=True
)

# Speeds up single-pair lookups used by /verify.
chain_records_collection.create_index(
    [("input_hash", ASCENDING), ("output_hash", ASCENDING)]
)