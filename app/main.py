# app/main.py
from fastapi import FastAPI
from app.routes import ingest, products, profiles, insights, recommend
from app import deps  # noqa: F401  # ensure services init at startup

app = FastAPI(title="FinAI (dev)")

# Register all routes under /ingest, /ingest/products, /profiles, /insights, /recommend
app.include_router(ingest.router)
app.include_router(products.router)
app.include_router(profiles.router)
app.include_router(insights.router)
app.include_router(recommend.router)

@app.get("/health")
def health():
    """
    Quick health probe to check the API is running.
    """
    return {"status": "ok"}
