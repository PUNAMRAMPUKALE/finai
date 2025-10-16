# app/deps.py
# Importing these triggers initialization once (embedded Weaviate etc.)
from app.services.weaviate_db import get_client  # noqa: F401
