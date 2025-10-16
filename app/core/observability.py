# app/core/observability.py
import time
import uuid
from typing import Callable
from fastapi import Request, Response, APIRouter
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest
from app.core.logging import get_logger

log = get_logger("obs")

# Prometheus registry and metrics
REGISTRY = CollectorRegistry()
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
    registry=REGISTRY,
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
    registry=REGISTRY,
)

SENSITIVE_PATHS = ("/api/v1/recommend", "/api/v1/insights")

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        req_id = str(uuid.uuid4())
        start = time.perf_counter()

        # Make request id accessible downstream
        request.state.request_id = req_id

        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "-"
        ua = request.headers.get("user-agent", "-")

        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        except Exception:
            # No body logging, only safe metadata
            log.exception(
                "unhandled_error",
                extra={"req_id": req_id, "method": method, "path": path, "client_ip": client_ip, "ua": ua},
            )
            raise
        finally:
            dur = time.perf_counter() - start
            # Metrics
            REQUEST_COUNT.labels(method=method, path=path, status_code=str(status)).inc()
            REQUEST_LATENCY.labels(method=method, path=path).observe(dur)
            # Access log (no bodies)
            log.info(
                "http_request",
                extra={
                    "req_id": req_id,
                    "method": method,
                    "path": path,
                    "status": status,
                    "duration_ms": round(dur * 1000, 2),
                    "client_ip": client_ip,
                    "ua": ua,
                },
            )

# Expose /metrics (Prometheus text format)
metrics_router = APIRouter()

@metrics_router.get("/metrics")
def metrics():
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)