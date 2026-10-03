"""HTTP API: POST /chat, /healthz, /metrics."""

import time

import anthropic
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field

from ai_assistant.agent import LlmUnavailableError, MaxStepsExceededError, ShoppingAgent
from ai_assistant.catalog import CatalogClient
from ai_assistant.config import GATEWAY_API_KEY_PLACEHOLDER, Settings
from ai_assistant.metrics import AGENT_STEPS, CHAT_DURATION, CHAT_REQUESTS
from ai_assistant.pricing import Pricing
from ai_assistant.tools import ToolExecutor

MAX_QUESTION_LENGTH = 2000


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)


class ChatResponse(BaseModel):
    answer: str
    steps: int


def create_app(agent: ShoppingAgent) -> FastAPI:
    app = FastAPI(title="ai-assistant")
    app.mount("/metrics", make_asgi_app())

    # Sync handler: FastAPI runs it in a worker thread, so blocking SDK calls are fine.
    @app.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest):
        started = time.perf_counter()
        try:
            answer = agent.answer(request.message)
        except LlmUnavailableError as error:
            return _failure("llm_error", 503, str(error))
        except MaxStepsExceededError as error:
            return _failure("max_steps", 500, str(error))
        finally:
            CHAT_DURATION.observe(time.perf_counter() - started)
        CHAT_REQUESTS.labels(outcome="success").inc()
        AGENT_STEPS.observe(answer.steps)
        return ChatResponse(answer=answer.text, steps=answer.steps)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    return app


def _failure(outcome: str, status_code: int, detail: str) -> JSONResponse:
    CHAT_REQUESTS.labels(outcome=outcome).inc()
    return JSONResponse(status_code=status_code, content={"error": detail})


def build_agent(settings: Settings) -> ShoppingAgent:
    client = anthropic.Anthropic(
        base_url=settings.llm_gateway_url,
        api_key=GATEWAY_API_KEY_PLACEHOLDER,
        max_retries=settings.llm_max_retries,
        timeout=settings.llm_timeout_seconds,
    )
    catalog = CatalogClient(settings.catalog_url, settings.catalog_timeout_seconds)
    return ShoppingAgent(
        client=client,
        tools=ToolExecutor(catalog),
        pricing=Pricing(settings.input_usd_per_million_tokens, settings.output_usd_per_million_tokens),
        model=settings.model,
        max_output_tokens=settings.max_output_tokens,
        max_steps=settings.max_agent_steps,
    )


app = create_app(build_agent(Settings.from_env()))
