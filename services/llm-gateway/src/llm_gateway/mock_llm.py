"""Free, deterministic stand-in for the Messages API.

It walks a client through one tool round trip, so agents exercise their tools:
1. a request with tools and no tool result yet -> call the first tool with empty input,
2. any other request -> a short text answer built from the latest tool result.
"""

import json
import uuid
from typing import Any

CHARS_PER_TOKEN = 4
ANSWER_PREVIEW_CHARS = 200


def create_message(request: dict[str, Any]) -> dict[str, Any]:
    tools = request.get("tools") or []
    messages = request.get("messages") or []
    latest_tool_result = _latest_tool_result(messages)

    if tools and latest_tool_result is None:
        content = [_tool_use_block(tools[0]["name"])]
        stop_reason = "tool_use"
    else:
        content = [{"type": "text", "text": _answer_text(latest_tool_result)}]
        stop_reason = "end_turn"

    return {
        "id": f"msg_mock_{uuid.uuid4().hex}",
        "type": "message",
        "role": "assistant",
        "model": request.get("model", "mock"),
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": _estimate_tokens(json.dumps(request)),
            "output_tokens": _estimate_tokens(json.dumps(content)),
        },
    }


def _latest_tool_result(messages: list[dict[str, Any]]) -> str | None:
    if not messages or messages[-1].get("role") != "user":
        return None
    content = messages[-1].get("content")
    if not isinstance(content, list):
        return None
    for block in reversed(content):
        if block.get("type") == "tool_result":
            return _tool_result_text(block.get("content"))
    return None


def _tool_result_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(block.get("text", "") for block in content if block.get("type") == "text")
    return ""


def _tool_use_block(tool_name: str) -> dict[str, Any]:
    return {"type": "tool_use", "id": f"toolu_mock_{uuid.uuid4().hex}", "name": tool_name, "input": {}}


def _answer_text(tool_result: str | None) -> str:
    if tool_result is None:
        return "[mock] Hello! Ask me about products in the store."
    return f"[mock] Here is what I found: {tool_result[:ANSWER_PREVIEW_CHARS]}"


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)
