from fastapi import FastAPI
from app.api.v1.routers import ingest, products, profiles, insights, recommend, crew, graph
from app.core.observability import ObservabilityMiddleware, metrics_router   # ✅ add

def create_app() -> FastAPI:
    app = FastAPI(title="FinAI", version="1.0")

    # ✅ observability: logs + latency metrics
    app.add_middleware(ObservabilityMiddleware)

    api_prefix = "/api/v1"
    app.include_router(ingest.router,   prefix=api_prefix)
    app.include_router(products.router, prefix=api_prefix)
    app.include_router(profiles.router, prefix=api_prefix)
    app.include_router(insights.router, prefix=api_prefix)
    app.include_router(recommend.router,prefix=api_prefix)
    app.include_router(crew.router,     prefix=api_prefix)
    app.include_router(graph.router,    prefix=api_prefix)

    # ✅ expose /metrics for Prometheus
    app.include_router(metrics_router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app

app = create_app()
