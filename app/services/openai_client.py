import os
from openai import OpenAI

def get_client():
    """
    Create a language model client.
    Automatically uses OpenRouter if OPENROUTER_API_KEY is set,
    otherwise defaults to OpenAI.
    """
    if os.getenv("OPENROUTER_API_KEY"):
        print("🔄 Using OpenRouter client")
        return OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
    elif os.getenv("OPENAI_API_KEY"):
        print("🧠 Using OpenAI client")
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    else:
        raise ValueError("❌ No API key found. Set OPENROUTER_API_KEY or OPENAI_API_KEY in .env")


def chat_complete(prompt: str, model: str = "mistralai/mistral-7b-instruct"):
    """
    Use OpenRouter (or OpenAI fallback) for chat completions.
    """
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a financial analysis assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content
