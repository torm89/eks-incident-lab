"""Forwards Messages API requests to the real Anthropic API."""

import httpx2 as httpx
from fastapi import Response

FORWARDED_HEADERS = ("anthropic-version", "anthropic-beta", "content-type")
MESSAGES_PATH = "/v1/messages"


class Upstream:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_seconds)

    async def create_message(self, body: bytes, request_headers: dict[str, str]) -> Response:
        headers = {name: request_headers[name] for name in FORWARDED_HEADERS if name in request_headers}
        # The real key lives only in the gateway; clients send a placeholder.
        headers["x-api-key"] = self._api_key
        upstream_response = await self._client.post(MESSAGES_PATH, content=body, headers=headers)
        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            media_type=upstream_response.headers.get("content-type"),
        )

    async def close(self) -> None:
        await self._client.aclose()
