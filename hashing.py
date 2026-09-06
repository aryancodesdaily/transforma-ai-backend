"""
hashing.py

Utility functions for generating SHA-256 hashes.

Used to create tamper-evident fingerprints of:
- input content
- generated output files
"""

import hashlib


def hash_content(content: str) -> str:
    """
    Generate SHA-256 hash of text content.
    """

    if not content:
        raise ValueError("Content cannot be empty.")

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def hash_file(file_path: str) -> str:
    """
    Generate SHA-256 hash of the actual file bytes.
    """

    with open(file_path, "rb") as file:
        file_bytes = file.read()

    if not file_bytes:
        raise ValueError("File cannot be empty.")

    return hashlib.sha256(file_bytes).hexdigest()