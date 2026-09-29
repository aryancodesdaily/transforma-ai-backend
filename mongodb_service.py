import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4

from hashing import hash_bytes
from mongodb import chain_records_collection

# prev_hash of the very first record in the chain.
GENESIS_HASH = "0" * 64

# Single shared lock for the whole process. Ensures that when several
# transformations are being generated concurrently (e.g. multiple
# outputs from one request), they are appended to the chain one at a
# time, each correctly linked to the record that came immediately
# before it.
_chain_lock = asyncio.Lock()


def _compute_record_hash(
    input_hash: str,
    output_hash: str,
    prev_hash: str,
    timestamp_str: str,
    transformation_details: dict
) -> str:
    """
    Deterministically hash everything that makes this record what it
    is: its own input/output, its link to the previous record, when
    it was created, and the parameters used. json.dumps with
    sort_keys guarantees the same dict always serializes identically.
    """

    details_json = json.dumps(transformation_details or {}, sort_keys=True)
    payload = f"{input_hash}{output_hash}{prev_hash}{timestamp_str}{details_json}"

    return hash_bytes(payload.encode("utf-8"))


async def store_transformation(
    input_hash: str,
    output_hash: str,
    user_id: str | None = None,
    transformation_details: dict | None = None
):
    """
    Append a new record to the tamper-evident chain.
    """

    async with _chain_lock:
        last_record = chain_records_collection.find_one(
            sort=[("sequence", -1)]
        )

        sequence = (last_record["sequence"] + 1) if last_record else 1
        prev_hash = last_record["record_hash"] if last_record else GENESIS_HASH

        timestamp_str = datetime.now(timezone.utc).isoformat()

        record_hash = _compute_record_hash(
            input_hash, output_hash, prev_hash, timestamp_str, transformation_details
        )

        record = {
            "sequence": sequence,
            "transformation_id": uuid4().hex,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "prev_hash": prev_hash,
            "record_hash": record_hash,
            "timestamp": timestamp_str,
            "user_id": user_id,
            "transformation_details": transformation_details or {}
        }

        chain_records_collection.insert_one(record)

        return {
            "transformation_id": record["transformation_id"],
            "sequence": sequence,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "record_hash": record_hash,
            "timestamp": timestamp_str
        }


def verify_transformation(input_hash: str, output_hash: str):
    """
    Verify whether an output was generated from a particular input.

    Returns one of three verdicts:

    1. input_file_never_received
    2. output_file_never_generated
    3. output_was_generated_by_input
    """

    any_record_for_input = chain_records_collection.find_one(
        {"input_hash": input_hash}
    )

    if any_record_for_input is None:
        return {
            "verdict": "input_file_never_received",
            "message": "This input was never received by the system."
        }

    matching_record = chain_records_collection.find_one(
        {"input_hash": input_hash, "output_hash": output_hash}
    )

    if matching_record is None:
        return {
            "verdict": "output_file_never_generated",
            "message": "This output was never generated from this input."
        }

    return {
        "verdict": "output_was_generated_by_input",
        "message": "This output was generated from this input.",
        "transformation_id": matching_record.get("transformation_id"),
        "timestamp": matching_record.get("timestamp"),
        "user_id": matching_record.get("user_id")
    }


def verify_chain_integrity():
    """
    Walk the entire chain in sequence order, recomputing each record's
    hash from its stored fields and checking:

    1. the record's own hash matches what is stored (nothing in the
       record itself was edited)
    2. the record's prev_hash matches the previous record's actual
       hash (the link has not been broken)
    3. sequence numbers have no gaps (no record was deleted)
    """

    records = list(
        chain_records_collection.find().sort("sequence", 1)
    )

    total_records = len(records)

    if total_records == 0:
        return {
            "chain_intact": True,
            "total_records": 0,
            "broken_at_sequence": None,
            "message": "No transformations recorded yet."
        }

    expected_sequence = 1
    expected_prev_hash = GENESIS_HASH

    for record in records:
        if record["sequence"] != expected_sequence:
            return {
                "chain_intact": False,
                "total_records": total_records,
                "broken_at_sequence": expected_sequence,
                "message": f"Record #{expected_sequence} is missing from the chain."
            }

        recomputed_hash = _compute_record_hash(
            record["input_hash"],
            record["output_hash"],
            record["prev_hash"],
            record["timestamp"],
            record.get("transformation_details", {})
        )

        if record["prev_hash"] != expected_prev_hash:
            return {
                "chain_intact": False,
                "total_records": total_records,
                "broken_at_sequence": record["sequence"],
                "message": f"Record #{record['sequence']} is not linked to the previous record."
            }

        if recomputed_hash != record["record_hash"]:
            return {
                "chain_intact": False,
                "total_records": total_records,
                "broken_at_sequence": record["sequence"],
                "message": f"Record #{record['sequence']} has been altered."
            }

        expected_prev_hash = record["record_hash"]
        expected_sequence += 1

    return {
        "chain_intact": True,
        "total_records": total_records,
        "broken_at_sequence": None,
        "message": "All records verified. Chain is intact."
    }


if __name__ == "__main__":
    from hashing import hash_content

    async def _test():
        input_hash = hash_content("Hello, this is a test.")
        output_hash = hash_content("This is generated output.")

        result = await store_transformation(
            input_hash=input_hash,
            output_hash=output_hash,
            user_id="test-user",
            transformation_details={"test": True}
        )

        print(result)
        print(verify_chain_integrity())

    asyncio.run(_test())