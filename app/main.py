from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator  # <- add

from app.api.v1.routers import auth, match

app = FastAPI(title="Startup→Investor Matcher (Minimal)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# expose /metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# Routes
app.include_router(auth.router,  prefix="/api/v1")
app.include_router(match.router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"ok": True}
