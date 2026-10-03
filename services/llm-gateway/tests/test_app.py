import pytest
from fastapi.testclient import TestClient

from llm_gateway.app import create_app
from llm_gateway.config import Mode, Settings

MESSAGE_REQUEST = {"model": "claude-haiku-4-5", "max_tokens": 100, "messages": [{"role": "user", "content": "hi"}]}


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        mode=Mode.MOCK,
        upstream_url="http://upstream.invalid",
        api_key="",
        upstream_timeout_seconds=1,
        mock_latency_ms=0,
    )
    return TestClient(create_app(settings))


def test_mock_mode_answers_messages(client):
    response = client.post("/v1/messages", json=MESSAGE_REQUEST)

    assert response.status_code == 200
    assert response.json()["type"] == "message"


def test_injected_status_returns_anthropic_style_error(client):
    client.post("/chaos/status/429")

    response = client.post("/v1/messages", json=MESSAGE_REQUEST)

    assert response.status_code == 429
    assert response.json()["error"]["type"] == "rate_limit_error"
    assert response.headers["retry-after"] == "2"


def test_overloaded_status_uses_overloaded_error_type(client):
    client.post("/chaos/status/529")

    response = client.post("/v1/messages", json=MESSAGE_REQUEST)

    assert response.json()["error"]["type"] == "overloaded_error"


def test_clearing_status_restores_normal_answers(client):
    client.post("/chaos/status/500")
    client.delete("/chaos/status")

    assert client.post("/v1/messages", json=MESSAGE_REQUEST).status_code == 200


def test_chaos_does_not_affect_health_check(client):
    client.post("/chaos/status/500")

    assert client.get("/healthz").status_code == 200


def test_invalid_status_is_rejected(client):
    assert client.post("/chaos/status/200").status_code == 400


def test_latency_injection_is_reported_in_state(client):
    client.post("/chaos/latency/1500")

    assert client.get("/chaos").json() == {"status_code": None, "latency_ms": 1500}

    client.delete("/chaos/latency")
    assert client.get("/chaos").json()["latency_ms"] == 0


def test_metrics_are_exposed(client):
    client.post("/v1/messages", json=MESSAGE_REQUEST)

    response = client.get("/metrics/")

    assert "llm_gateway_requests_total" in response.text
