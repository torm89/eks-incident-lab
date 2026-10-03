import anthropic
import httpx2 as httpx
import pytest

from ai_assistant.agent import LlmUnavailableError, MaxStepsExceededError, ShoppingAgent
from ai_assistant.pricing import Pricing
from ai_assistant.tools import ToolExecutor
from fakes import FakeAnthropic, FakeCatalog, text_message, tool_use_message


def make_agent(client: FakeAnthropic, max_steps: int = 5) -> ShoppingAgent:
    return ShoppingAgent(
        client=client,
        tools=ToolExecutor(FakeCatalog()),
        pricing=Pricing(1.0, 5.0),
        model="claude-haiku-4-5",
        max_output_tokens=1024,
        max_steps=max_steps,
    )


def status_error(status_code: int) -> anthropic.APIStatusError:
    request = httpx.Request("POST", "http://llm-gateway/v1/messages")
    response = httpx.Response(status_code, request=request)
    return anthropic.APIStatusError("injected", response=response, body=None)


def test_answers_directly_without_tools():
    agent = make_agent(FakeAnthropic([text_message("Hello!")]))

    answer = agent.answer("hi")

    assert answer.text == "Hello!"
    assert answer.steps == 1


def test_runs_tool_and_sends_result_back():
    client = FakeAnthropic([tool_use_message("search_products", {"max_price": 50}), text_message("Pocket Watch, 40")])

    answer = make_agent(client).answer("gift under 50?")

    assert answer.steps == 2
    tool_result = client.requests[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "toolu_search_products"
    assert "Pocket Watch" in tool_result["content"]


def test_uses_configured_model_and_tools():
    client = FakeAnthropic([text_message("ok")])

    make_agent(client).answer("hi")

    assert client.requests[0]["model"] == "claude-haiku-4-5"
    assert {tool["name"] for tool in client.requests[0]["tools"]} == {"search_products", "get_product", "list_tags"}


def test_stops_after_max_steps():
    looping = [tool_use_message("list_tags", {}) for _ in range(3)]

    with pytest.raises(MaxStepsExceededError):
        make_agent(FakeAnthropic(looping), max_steps=3).answer("loop forever")


def test_llm_http_error_becomes_llm_unavailable():
    with pytest.raises(LlmUnavailableError, match="429"):
        make_agent(FakeAnthropic([status_error(429)])).answer("hi")


def test_cost_is_computed_from_usage():
    assert Pricing(1.0, 5.0).cost_usd(input_tokens=1_000_000, output_tokens=200_000) == pytest.approx(2.0)
