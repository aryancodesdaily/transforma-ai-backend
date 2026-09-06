import os

from dotenv import load_dotenv

load_dotenv()

LLM_API_KEY = os.getenv("LLM_API_KEY")

LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

HF_TOKEN = os.getenv("HF_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")


def get_allowed_origins() -> list[str]:
    """Return the comma-separated browser origins permitted to call the API."""
    configured_origins = os.getenv("ALLOWED_ORIGINS", "")
    origins = [
        origin.strip().rstrip("/")
        for origin in configured_origins.split(",")
        if origin.strip()
    ]

    return origins or [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


ALLOWED_ORIGINS = get_allowed_origins()
