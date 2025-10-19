from fastapi import FastAPI
from app.api.v1.routers import ingest, products, profiles, insights, recommend, crew, graph
from app.core.observability import ObservabilityMiddleware, metrics_router   # ✅ add
from app.api.v1.routers import startups, investors

def create_app() -> FastAPI:
    app = FastAPI(title="FinAI", version="1.0")

    # ✅ observability: logs + latency metrics
    app.add_middleware(ObservabilityMiddleware)

    API_V1 = "/api/v1"
    app.include_router(ingest.router,    prefix=API_V1)
    app.include_router(products.router,  prefix=API_V1)
    app.include_router(profiles.router,  prefix=API_V1)
    app.include_router(insights.router,  prefix=API_V1)
    app.include_router(recommend.router, prefix=API_V1)
    app.include_router(crew.router,      prefix=API_V1)
    app.include_router(graph.router,     prefix=API_V1)
    app.include_router(startups.router,  prefix=API_V1)
    app.include_router(investors.router, prefix=API_V1)


    app.include_router(metrics_router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app

app = create_app()
