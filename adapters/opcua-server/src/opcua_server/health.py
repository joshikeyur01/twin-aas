"""Liveness, readiness, and metrics endpoints (portfolio convention;
argued in twin-services ADR-0004).

Small and deliberately duplicated across this repo's processes rather than
shared: readiness is a statement about *this* process's dependencies.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import cast

from fastapi import FastAPI, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, Gauge, generate_latest

ReadinessProbe = Callable[[], Mapping[str, bool]]


def _service_ready_gauge() -> Gauge:
    """In production each process is its own interpreter; only the test
    suite imports several at once, colliding on this shared gauge name."""
    try:
        return Gauge(
            "twin_service_ready",
            "1 when every dependency check passes, else 0.",
            ["service"],
        )
    except ValueError:
        return cast(Gauge, REGISTRY._names_to_collectors["twin_service_ready"])


_READY = _service_ready_gauge()


def build_health_app(service: str, readiness: ReadinessProbe) -> FastAPI:
    """FastAPI app serving /healthz/live, /healthz/ready, and /metrics."""
    app = FastAPI(title=service)
    ready_gauge = _READY.labels(service=service)

    @app.get("/healthz/live")
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/healthz/ready")
    async def ready(response: Response) -> dict[str, object]:
        checks = dict(readiness())
        ok = all(checks.values())
        ready_gauge.set(1 if ok else 0)
        if not ok:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "ready" if ok else "degraded", "checks": checks}

    @app.get("/metrics")
    async def metrics() -> Response:
        ready_gauge.set(1 if all(readiness().values()) else 0)
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app
