from datetime import datetime, timezone
from uuid import uuid4

from mongodb import transformations_collection


def store_transformation(
    input_hash: str,
    output_hash: str,
    user_id: str | None = None,
    transformation_details: dict | None = None
):
    """
    Store a generated output against its input hash.

    If the input hash already exists:
        add the new output to the existing document.

    If the input hash does not exist:
        create a new document.
    """

    now = datetime.now(timezone.utc)

    output_record = {
        "transformation_id": uuid4().hex,
        "output_hash": output_hash,
        "timestamp": now,
        "user_id": user_id,
        "transformation_details": transformation_details or {}
    }

    # First try to find the existing input block
    existing_document = transformations_collection.find_one(
        {"input_hash": input_hash}
    )

    if existing_document:
        # Same input -> add another output to the existing block
        transformations_collection.update_one(
            {"input_hash": input_hash},
            {
                "$set": {
                    "last_updated_at": now
                },
                "$push": {
                    "outputs": output_record
                },
                "$inc": {
                    "transformation_count": 1
                }
            }
        )

    else:
        # New input -> create a new block
        transformations_collection.insert_one(
            {
                "input_hash": input_hash,
                "created_at": now,
                "last_updated_at": now,
                "transformation_count": 1,
                "outputs": [
                    output_record
                ]
            }
        )

    return {
        "transformation_id": output_record["transformation_id"],
        "input_hash": input_hash,
        "output_hash": output_hash,
        "timestamp": now
    }
    
if __name__ == "__main__":
    from hashing import hash_content

    test_input = "Hello, this is a test."

    input_hash = hash_content(test_input)
    output_hash = hash_content("This is generated 1 output.")

    result = store_transformation(
        input_hash=input_hash,
        output_hash=output_hash,
        user_id="test-user",
        transformation_details={
            "test": True
        }
    )

    print(result)