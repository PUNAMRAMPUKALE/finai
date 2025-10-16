# app/services/openai_client.py
import os
from openai import OpenAI

def get_client():
    return OpenAI(
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_API_BASE"),  # Groq’s OpenAI-compatible base
    )

def chat_complete(prompt: str, model: str | None = None) -> str:
    client = get_client()
    model = model or os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful, factual financial assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=700,
    )
    return (resp.choices[0].message.content or "").strip()