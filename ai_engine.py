from groq import Groq

from config import LLM_API_KEY, LLM_MODEL

if not LLM_API_KEY:
    raise ValueError("LLM_API_KEY is missing from .env")

client = Groq(api_key=LLM_API_KEY)


def generate_content(system_instruction: str, user_prompt: str) -> str:
    """
    Send instructions and user prompt to the Groq LLM
    and return the generated text.
    """

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_instruction
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.3
    )

    return response.choices[0].message.content