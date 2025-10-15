# app/config.py
from pydantic import BaseModel
from dotenv import load_dotenv
import os

# Load variables from .env into environment at app startup
load_dotenv()

class Settings(BaseModel):
    app_env: str = os.getenv("APP_ENV", "dev")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # OpenAI key (required to generate answers/explanations)
    openai_api_key: str = os.getenv("LLM_API_KEY", "")

    # Local embedded Weaviate config (no external DB needed)
    weaviate_embedded: bool = os.getenv("WEAVIATE_EMBEDDED", "1") == "1"
    weaviate_data_path: str = os.getenv("WEAVIATE_DATA_PATH", ".weaviate")

    # Optional Neo4j (not required for this MVP run)
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "testpass")

settings = Settings()
