from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from ai_assistant.app import create_app
from fakes import FakeAnthropic, text_message, tool_use_message
from test_agent import make_agent, status_error

GEN_AI_LABELS = {"gen_ai_operation_name": "chat", "gen_ai_system": "anthropic", "gen_ai_request_model": "claude-haiku-4-5"}


def sample(name: str, labels: dict[str, str]) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


def chat(responses: list) -> int:
    client = TestClient(create_app(make_agent(FakeAnthropic(responses))))
    return client.post("/chat", json={"message": "gift under 50?"}).status_code


def test_successful_chat_records_open_telemetry_gen_ai_metrics():
    calls_before = sample("gen_ai_client_operation_duration_seconds_count", {**GEN_AI_LABELS, "error_type": ""})
    input_tokens_before = sample("gen_ai_client_token_usage_sum", {**GEN_AI_LABELS, "gen_ai_token_type": "input"})

    assert chat([tool_use_message("search_products", {}), text_message("Pocket Watch")]) == 200

    assert sample("gen_ai_client_operation_duration_seconds_count", {**GEN_AI_LABELS, "error_type": ""}) == calls_before + 2
    assert sample("gen_ai_client_token_usage_sum", {**GEN_AI_LABELS, "gen_ai_token_type": "input"}) == input_tokens_before + 2000
    assert sample("ai_assistant_tool_call_duration_seconds_count", {"tool": "search_products", "outcome": "success"}) >= 1


def test_failed_llm_call_sets_error_type_and_chat_outcome():
    errors_before = sample("gen_ai_client_operation_duration_seconds_count", {**GEN_AI_LABELS, "error_type": "529"})
    failures_before = sample("ai_assistant_chat_duration_seconds_count", {"outcome": "llm_error"})

    assert chat([status_error(529)]) == 503

    assert sample("gen_ai_client_operation_duration_seconds_count", {**GEN_AI_LABELS, "error_type": "529"}) == errors_before + 1
    assert sample("ai_assistant_chat_duration_seconds_count", {"outcome": "llm_error"}) == failures_before + 1


def test_no_chat_is_left_in_progress():
    chat([text_message("hi")])

    assert sample("ai_assistant_chat_requests_in_progress", {}) == 0
