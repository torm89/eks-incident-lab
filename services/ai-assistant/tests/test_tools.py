import json

from ai_assistant.tools import TOOL_DEFINITIONS, ToolExecutor
from fakes import FakeCatalog


def test_search_filters_by_max_price():
    result = ToolExecutor(FakeCatalog()).run("search_products", {"max_price": 50})

    assert not result.is_error
    assert [p["name"] for p in json.loads(result.content)] == ["Pocket Watch"]


def test_search_returns_tag_names_only():
    result = ToolExecutor(FakeCatalog()).run("search_products", {"tag": "bags"})

    assert json.loads(result.content) == [{"id": "p2", "name": "Leather Bag", "price": 120, "tags": ["bags"]}]


def test_catalog_failure_becomes_error_result():
    result = ToolExecutor(FakeCatalog(failure=TimeoutError("catalog timed out"))).run("list_tags", {})

    assert result.is_error
    assert "catalog timed out" in result.content


def test_unknown_tool_is_an_error_result():
    result = ToolExecutor(FakeCatalog()).run("delete_everything", {})

    assert result.is_error


def test_every_defined_tool_has_a_handler():
    executor = ToolExecutor(FakeCatalog())

    for tool in TOOL_DEFINITIONS:
        assert "Unknown tool" not in executor.run(tool["name"], {"product_id": "p1"}).content
