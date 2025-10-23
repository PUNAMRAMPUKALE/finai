# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

# Existing routers
from app.api.v1.routers import auth, match
# Add your new investors router here (but not investor_ingest)
from app.api.v1.routers import investors

app = FastAPI(title="Startup→Investor Matcher")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# Include routers
app.include_router(auth.router,  prefix="/api/v1")
app.include_router(match.router, prefix="/api/v1")
app.include_router(investors.router, prefix="/api/v1")  # ✅ works without investor_ingest

@app.get("/health")
def health():
    return {"ok": True}
