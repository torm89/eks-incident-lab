"""Client for the Retail Store catalog API."""

from typing import Any

import httpx2 as httpx

PRODUCTS_PER_PAGE = 50


class CatalogClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout_seconds)

    def list_products(self, tag: str | None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"size": PRODUCTS_PER_PAGE}
        if tag:
            params["tags"] = tag
        return self._get("/catalog/products", params)

    def get_product(self, product_id: str) -> dict[str, Any]:
        return self._get(f"/catalog/products/{product_id}")

    def list_tags(self) -> list[dict[str, Any]]:
        return self._get("/catalog/tags")

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._client.close()
