"""Runtime configuration, read once from environment variables."""

import os
from dataclasses import dataclass
from enum import StrEnum


class Mode(StrEnum):
    MOCK = "mock"
    REAL = "real"


@dataclass(frozen=True)
class Settings:
    mode: Mode
    upstream_url: str
    api_key: str
    upstream_timeout_seconds: float
    mock_latency_ms: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            mode=Mode(os.getenv("LLM_MODE", Mode.MOCK)),
            upstream_url=os.getenv("UPSTREAM_URL", "https://api.anthropic.com"),
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            upstream_timeout_seconds=float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "120")),
            mock_latency_ms=int(os.getenv("MOCK_LATENCY_MS", "400")),
        )
