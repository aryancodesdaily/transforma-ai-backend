"""
gemini_engine.py

Handles image-related AI features.

The external function names are kept unchanged so the rest of the
application does not need to know which AI provider is being used.

Internally:
- Vision: Hugging Face + Qwen2.5-VL
- Image generation: Hugging Face + FLUX.1-schnell
"""

import base64

from huggingface_hub import InferenceClient

from config import HF_TOKEN


_client = None


def _get_client() -> InferenceClient:
    """
    Lazily create the Hugging Face client only when an image feature
    is actually used.
    """
    global _client

    if _client is None:
        if not HF_TOKEN:
            raise ValueError(
                "HF_TOKEN is missing from .env. "
                "Add your Hugging Face API token to use image features."
            )

        _client = InferenceClient(
            provider="auto",
            api_key=HF_TOKEN,
        )

    return _client


def extract_content_from_image(
    image_bytes: bytes,
    mime_type: str
) -> str:
    """
    Use a Hugging Face vision-language model to read/describe an
    uploaded image and return the extracted content as plain text.

    Function name intentionally kept unchanged so the rest of the
    application does not need to change.
    """

    client = _get_client()

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    image_data_url = (
        f"data:{mime_type};base64,{image_base64}"
    )

    response = client.chat_completion(
        model="Qwen/Qwen2.5-VL-3B-Instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract all readable text from this image "
                            "and describe any relevant visual content "
                            "(charts, diagrams, photos, layout) factually "
                            "and in detail. Do not add opinions or "
                            "information that is not visible in the image."
                        ),
                    },
                ],
            }
        ],
        max_tokens=2000,
    )

    text = response.choices[0].message.content

    if isinstance(text, list):
        text = " ".join(
            item.get("text", "")
            for item in text
            if isinstance(item, dict)
        )

    text = (text or "").strip()

    if not text:
        raise ValueError(
            "Hugging Face vision model could not extract any content "
            "from the image."
        )

    return text


def generate_image_from_content(
    content: str,
    output_path: str,
    language: str = "English"
) -> None:
    """
    Turn transformed text content into a generated image using
    Hugging Face + FLUX.1-schnell.

    Function name intentionally kept unchanged so the rest of the
    application does not need to change.
    """

    client = _get_client()

    image_prompt = (
        "Create a single clear, professional infographic based strictly "
        "on the content provided below.\n\n"

        "LANGUAGE REQUIREMENT:\n"
        f"ALL VISIBLE TEXT IN THE IMAGE MUST BE WRITTEN ONLY IN {language}.\n"
        f"The selected output language is {language}.\n"
        "Do not use any other language.\n\n"

        "TEXT ACCURACY RULES:\n"
        "1. Use only meaningful words and sentences from the provided "
        "content.\n"
        "2. Do not invent words, phrases, headings, labels, numbers, "
        "names, dates, statistics, or facts.\n"
        "3. Do not replace words with synonyms or another language.\n"
        "4. Do not generate random or meaningless text.\n"
        "5. Preserve important names, numbers, dates, and terminology "
        "accurately.\n"
        "6. If a piece of text cannot be rendered accurately, leave it "
        "out instead of generating incorrect text.\n"
        "7. Keep all headings and labels short, clear, and readable.\n"
        "8. Do not add information that is not supported by the content.\n\n"

        "VISUAL REQUIREMENTS:\n"
        "Create a clean, professional infographic with a logical layout, "
        "clear sections, appropriate icons or illustrations, and good "
        "visual hierarchy. The visual design should support the content "
        "without changing its meaning.\n\n"

        "CONTENT:\n"
        f"{content}"
    )

    image = client.text_to_image(
        prompt=image_prompt,
        model="black-forest-labs/FLUX.1-schnell",
    )

    image.save(output_path)