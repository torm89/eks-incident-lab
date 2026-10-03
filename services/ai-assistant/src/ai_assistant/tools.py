"""Tools Claude can call, and their implementations on top of the catalog API."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from ai_assistant.metrics import TOOL_CALLS

DEFAULT_RESULT_LIMIT = 5

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "search_products",
        "description": (
            "Search the store catalog. Returns matching products with id, name, price and tags. "
            "Use it whenever the customer asks what the store sells."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "Only products with this tag. Get valid tags from list_tags."},
                "max_price": {"type": "integer", "description": "Only products at or below this price."},
                "limit": {"type": "integer", "description": f"Maximum number of results, default {DEFAULT_RESULT_LIMIT}."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_product",
        "description": "Get full details of one product, including its description.",
        "input_schema": {
            "type": "object",
            "properties": {"product_id": {"type": "string", "description": "Product id from search_products."}},
            "required": ["product_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_tags",
        "description": "List the product tags (categories) available in the store.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


class Catalog(Protocol):
    def list_products(self, tag: str | None) -> list[dict[str, Any]]: ...
    def get_product(self, product_id: str) -> dict[str, Any]: ...
    def list_tags(self) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class ToolResult:
    content: str
    is_error: bool


class ToolExecutor:
    def __init__(self, catalog: Catalog) -> None:
        self._catalog = catalog
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "search_products": self._search_products,
            "get_product": lambda tool_input: catalog.get_product(tool_input["product_id"]),
            "list_tags": lambda _: catalog.list_tags(),
        }

    def run(self, tool_name: str, tool_input: dict[str, Any]) -> ToolResult:
        handler = self._handlers.get(tool_name)
        if handler is None:
            TOOL_CALLS.labels(tool=tool_name, outcome="unknown_tool").inc()
            return ToolResult(f"Unknown tool: {tool_name}", is_error=True)
        try:
            result = handler(tool_input)
        except Exception as error:  # Any failure is reported back to Claude, not raised.
            TOOL_CALLS.labels(tool=tool_name, outcome="error").inc()
            return ToolResult(f"Tool {tool_name} failed: {error}", is_error=True)
        TOOL_CALLS.labels(tool=tool_name, outcome="success").inc()
        return ToolResult(json.dumps(result), is_error=False)

    def _search_products(self, tool_input: dict[str, Any]) -> list[dict[str, Any]]:
        products = self._catalog.list_products(tool_input.get("tag"))
        max_price = tool_input.get("max_price")
        if max_price is not None:
            products = [product for product in products if product["price"] <= max_price]
        limit = tool_input.get("limit", DEFAULT_RESULT_LIMIT)
        return [_summary(product) for product in products[:limit]]


def _summary(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": product["id"],
        "name": product["name"],
        "price": product["price"],
        "tags": [tag["name"] for tag in product.get("tags", [])],
    }
