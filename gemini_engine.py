import os
import base64
from io import BytesIO

from google import genai
from google.genai import types

from config import GEMINI_API_KEY

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env")

_client = genai.Client(api_key=GEMINI_API_KEY)



from huggingface_hub import InferenceClient

HF_API_KEY = os.getenv("HF_API_KEY")
HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL")

if not HF_API_KEY:
    raise ValueError("HF_API_KEY is missing from .env")

if not HF_IMAGE_MODEL:
    raise ValueError("HF_IMAGE_MODEL is missing from .env")

_hf_client = InferenceClient(
    api_key=HF_API_KEY
)


def extract_content_from_image(image_bytes: bytes, mime_type: str) -> str:
    response = _client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            (
                "Extract all readable text from this image and describe "
                "any relevant visual content (charts, diagrams, photos, "
                "layout) factually and in detail. Do not add opinions or "
                "information that is not visible in the image."
            ),
        ],
    )

    text = (response.text or "").strip()

    if not text:
        raise ValueError("Gemini could not extract any content from the image.")

    return text


def generate_image_from_content(
    content: str,
    output_path: str,
    language: str = "English"
) -> None:

    image_prompt = (
        "Create a single clear, professional infographic based strictly "
        "on the content provided below.\n\n"

        f"All visible text must be written only in {language}.\n"

        "Do not invent facts, numbers, names, dates, or information.\n"
        "Use a clean professional infographic layout with clear visual "
        "hierarchy, icons, illustrations, and logical sections.\n\n"
        "CONTENT:\n"
        f"{content}"
    )

    image = _hf_client.text_to_image(
        prompt=image_prompt,
        model=HF_IMAGE_MODEL
    )

    image.save(output_path)