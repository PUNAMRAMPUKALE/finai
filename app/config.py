import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    app_env: str = os.getenv("APP_ENV", "dev")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # LLM/Embeddings not needed beyond local ST model
    # Vector DB (Weaviate embedded/local)
    weaviate_embedded: bool = os.getenv("WEAVIATE_EMBEDDED", "1") == "1"
    weaviate_data_path: str = os.getenv("WEAVIATE_DATA_PATH", ".weaviate")

    # Auth
    jwt_secret: str = os.getenv("JWT_SECRET", "dev_secret_change_me")
    jwt_algo: str = os.getenv("JWT_ALGO", "HS256")
    jwt_ttl_seconds: int = int(os.getenv("JWT_TTL_SECONDS", str(24 * 60 * 60)))

settings = Settings()