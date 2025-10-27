# app/main.py
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.db.core import init_db
from app.api.v1.routers import auth, match, investors, products

app = FastAPI(title="Startup→Investor Matcher")

# CORS: set CORS_ORIGINS in Render (comma-separated)
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if not origins:
    origins = ["http://localhost:5173"]  # dev default

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

@app.on_event("startup")
def on_startup():
    init_db()

# Routers
app.include_router(auth.router,      prefix="/api/v1")
app.include_router(match.router,     prefix="/api/v1")
app.include_router(investors.router, prefix="/api/v1")
app.include_router(products.router,  prefix="/api/v1")

@app.get("/health")
def health():
    return {"ok": True}
