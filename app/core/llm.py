import os
from openai import OpenAI

def _client():
    return OpenAI(api_key=os.getenv("LLM_API_KEY"), base_url=os.getenv("LLM_API_BASE"))

def chat_complete(system: str, user: str, *, model: str | None = None, temperature=0.2, max_tokens=700) -> str:
    resp = _client().chat.completions.create(
        model=model or os.getenv("LLM_MODEL", "llama-3.1-8b-instant"),
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        temperature=temperature, max_tokens=max_tokens
    )
    return (resp.choices[0].message.content or "").strip()