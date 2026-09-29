"""
hashing.py

Utility functions for generating SHA-256 hashes.

Byte-level hashing is the single source of truth: it is deterministic
regardless of which library extracted text from a file, and it works
for any file type (including images) without needing to re-describe
the content through an AI model just to hash it.
"""

import hashlib


def hash_bytes(data: bytes) -> str:
    """
    Generate SHA-256 hash of raw bytes.
    """

    if not data:
        raise ValueError("Data cannot be empty.")

    return hashlib.sha256(data).hexdigest()


def hash_content(content: str) -> str:
    """
    Generate SHA-256 hash of raw pasted text (UTF-8 encoded), for the
    text-input path where no uploaded file exists.
    """

    if not content:
        raise ValueError("Content cannot be empty.")

    return hash_bytes(content.encode("utf-8"))


def hash_file(file_path: str) -> str:
    """
    Generate SHA-256 hash of a file's raw bytes, given its path.
    """

    with open(file_path, "rb") as file:
        file_bytes = file.read()

    return hash_bytes(file_bytes)