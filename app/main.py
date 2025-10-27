from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.db.core import init_db
from app.api.v1.routers import auth, match, investors, products



app = FastAPI(title="Startup→Investor Matcher")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(auth.router,  prefix="/api/v1")
app.include_router(match.router, prefix="/api/v1")
app.include_router(investors.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
from app.api.v1.routers import auth, match, investors, products


@app.get("/health")
def health():
    return {"ok": True}