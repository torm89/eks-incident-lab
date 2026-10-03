from llm_gateway import mock_llm

SEARCH_TOOL = {"name": "search_products", "input_schema": {"type": "object", "properties": {}}}


def test_first_request_with_tools_calls_the_first_tool():
    request = {"model": "m", "tools": [SEARCH_TOOL], "messages": [{"role": "user", "content": "gift ideas?"}]}

    message = mock_llm.create_message(request)

    assert message["stop_reason"] == "tool_use"
    assert message["content"][0]["type"] == "tool_use"
    assert message["content"][0]["name"] == "search_products"
    assert message["content"][0]["input"] == {}


def test_request_after_tool_result_returns_text_answer():
    request = {
        "model": "m",
        "tools": [SEARCH_TOOL],
        "messages": [
            {"role": "user", "content": "gift ideas?"},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "search_products", "input": {}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "Pocket Watch"}]},
        ],
    }

    message = mock_llm.create_message(request)

    assert message["stop_reason"] == "end_turn"
    assert "Pocket Watch" in message["content"][0]["text"]


def test_request_without_tools_returns_text_answer():
    message = mock_llm.create_message({"model": "m", "messages": [{"role": "user", "content": "hi"}]})

    assert message["stop_reason"] == "end_turn"
    assert message["content"][0]["type"] == "text"


def test_usage_reports_positive_token_counts():
    message = mock_llm.create_message({"model": "m", "messages": [{"role": "user", "content": "hi"}]})

    assert message["usage"]["input_tokens"] > 0
    assert message["usage"]["output_tokens"] > 0
