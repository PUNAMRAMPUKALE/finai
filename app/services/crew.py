# app/services/crew.py
import os
from crewai import Agent, Crew, Task, LLM

def get_llm():
    # Single-source env you set:
    # LLM_PROVIDER=groq
    # LLM_API_KEY=...
    # LLM_API_BASE=https://api.groq.com/openai/v1
    # LLM_MODEL=llama-3.1-8b-instant
    #
    # CrewAI uses LiteLLM under the hood. For Groq models, prefix with "groq/".
    # If your LLM_MODEL is 'llama-3.1-8b-instant', CrewAI expects 'groq/llama-3.1-8b-instant'.
    model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
    if not model.startswith("groq/"):
        model = f"groq/{model}"

    return LLM(
        model=model,
        api_key=os.getenv("LLM_API_KEY"),
        api_base=os.getenv("LLM_API_BASE"),  # Groq OpenAI-compatible base
        temperature=0.2,
    )

def build_crew():
    llm = get_llm()

    researcher = Agent(
        role="Research Analyst",
        goal="Answer the question with concise facts and inline bracket citations like [1], [2].",
        backstory="ETF analyst who uses the RAG tool.",
        llm=llm,
        allow_delegation=False,
        max_iter=1,
        verbose=False,
    )

    matcher = Agent(
        role="Product Matcher",
        goal="Return the top-3 product matches as JSON with an explanation.",
        backstory="Maps a user's profile to suitable products.",
        llm=llm,
        # ⬇️ IMPORTANT: no tools list here anymore
        allow_delegation=False,
        max_iter=1,
        verbose=False,
    )

    task_research = Task(
        description=(
            "Use RAG to answer the user question with citations.\n"
            "Question: {question}\n"
            "Return a short answer with inline citations like [1], [2]."
        ),
        agent=researcher,
        async_execution=False,
        expected_output="A short paragraph with inline citations."
    )

    # ⬇️ We provide the precomputed tool JSON as input; the agent just returns it.
    task_match = Task(
        description=(
            "You are NOT to call any tools.\n"
            "You are given a PRECOMPUTED product-match JSON. "
            "Return it EXACTLY as-is.\n\n"
            "PRODUCT_MATCH_JSON:\n{product_match_json}"
        ),
        agent=matcher,
        async_execution=False,
        expected_output="The exact JSON string (no extra text)."
    )

    return Crew(
        agents=[researcher, matcher],
        tasks=[task_research, task_match],
        process="sequential"
    )
