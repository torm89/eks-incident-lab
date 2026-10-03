"""HTTP API: /v1/messages (mock or real), /chaos/* (fault injection), /healthz, /metrics."""

import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from llm_gateway import mock_llm
from llm_gateway.api_errors import error_response
from llm_gateway.chaos import ChaosState, InvalidFaultError
from llm_gateway.config import Mode, Settings
from llm_gateway.metrics import INJECTED_FAULTS, REQUEST_DURATION, REQUESTS
from llm_gateway.upstream import Upstream

MILLISECONDS_PER_SECOND = 1000


def create_app(settings: Settings) -> FastAPI:
    chaos = ChaosState()
    upstream = Upstream(settings.upstream_url, settings.api_key, settings.upstream_timeout_seconds)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await upstream.close()

    app = FastAPI(title="llm-gateway", lifespan=lifespan)
    app.mount("/metrics", make_asgi_app())

    @app.post("/v1/messages")
    async def create_message(request: Request) -> Response:
        started = time.perf_counter()
        response = await _answer(request)
        REQUESTS.labels(mode=settings.mode, status=response.status_code).inc()
        REQUEST_DURATION.labels(mode=settings.mode).observe(time.perf_counter() - started)
        return response

    async def _answer(request: Request) -> Response:
        if chaos.latency_ms:
            INJECTED_FAULTS.labels(fault="latency").inc()
            await asyncio.sleep(chaos.latency_ms / MILLISECONDS_PER_SECOND)
        if chaos.status_code is not None:
            INJECTED_FAULTS.labels(fault="status").inc()
            return error_response(chaos.status_code, "Injected by llm-gateway chaos API")
        if settings.mode is Mode.REAL:
            return await upstream.create_message(await request.body(), dict(request.headers))
        await asyncio.sleep(settings.mock_latency_ms / MILLISECONDS_PER_SECOND)
        return JSONResponse(mock_llm.create_message(await request.json()))

    @app.get("/chaos")
    async def chaos_state() -> dict:
        return {"status_code": chaos.status_code, "latency_ms": chaos.latency_ms}

    @app.post("/chaos/status/{status_code}")
    async def inject_status(status_code: int) -> dict:
        _apply(lambda: chaos.inject_status(status_code))
        return await chaos_state()

    @app.delete("/chaos/status")
    async def clear_status() -> dict:
        chaos.clear_status()
        return await chaos_state()

    @app.post("/chaos/latency/{latency_ms}")
    async def inject_latency(latency_ms: int) -> dict:
        _apply(lambda: chaos.inject_latency(latency_ms))
        return await chaos_state()

    @app.delete("/chaos/latency")
    async def clear_latency() -> dict:
        chaos.clear_latency()
        return await chaos_state()

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"status": "ok", "mode": settings.mode}

    return app


def _apply(inject) -> None:
    try:
        inject()
    except InvalidFaultError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


app = create_app(Settings.from_env())
