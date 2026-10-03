"""Test doubles for the catalog and the Anthropic client."""

from types import SimpleNamespace
from typing import Any

PRODUCTS = [
    {"id": "p1", "name": "Pocket Watch", "price": 40, "description": "Classic.", "tags": [{"name": "accessories"}]},
    {"id": "p2", "name": "Leather Bag", "price": 120, "description": "Large.", "tags": [{"name": "bags"}]},
]


class FakeCatalog:
    def __init__(self, failure: Exception | None = None) -> None:
        self._failure = failure

    def list_products(self, tag: str | None) -> list[dict[str, Any]]:
        self._fail_if_needed()
        return [p for p in PRODUCTS if tag is None or tag in [t["name"] for t in p["tags"]]]

    def get_product(self, product_id: str) -> dict[str, Any]:
        self._fail_if_needed()
        return next(p for p in PRODUCTS if p["id"] == product_id)

    def list_tags(self) -> list[dict[str, Any]]:
        self._fail_if_needed()
        return [{"name": "accessories"}, {"name": "bags"}]

    def _fail_if_needed(self) -> None:
        if self._failure:
            raise self._failure


def text_message(text: str) -> SimpleNamespace:
    return _message("end_turn", [SimpleNamespace(type="text", text=text)])


def tool_use_message(tool_name: str, tool_input: dict[str, Any]) -> SimpleNamespace:
    block = SimpleNamespace(type="tool_use", id=f"toolu_{tool_name}", name=tool_name, input=tool_input)
    return _message("tool_use", [block])


def _message(stop_reason: str, content: list[SimpleNamespace]) -> SimpleNamespace:
    usage = SimpleNamespace(input_tokens=1000, output_tokens=200)
    return SimpleNamespace(stop_reason=stop_reason, content=content, usage=usage)


class FakeAnthropic:
    """Returns scripted responses (or raises scripted errors) and records every request."""

    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.requests: list[dict[str, Any]] = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **request: Any) -> Any:
        self.requests.append(request)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response
