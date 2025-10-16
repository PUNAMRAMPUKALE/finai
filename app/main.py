from fastapi import FastAPI
from app.api.v1.routers import ingest, products, profiles, insights, recommend, crew, graph

app = FastAPI(title="FinAI")

API_PREFIX = "/api/v1"
app.include_router(ingest.router,   prefix=API_PREFIX)
app.include_router(products.router, prefix=API_PREFIX)
app.include_router(profiles.router, prefix=API_PREFIX)
app.include_router(insights.router, prefix=API_PREFIX)
app.include_router(recommend.router,prefix=API_PREFIX)
app.include_router(crew.router,     prefix=API_PREFIX)
app.include_router(graph.router,    prefix=API_PREFIX)

@app.get("/health")
def health():
    return {"status":"ok"}