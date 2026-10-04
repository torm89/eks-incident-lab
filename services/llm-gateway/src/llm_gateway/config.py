"""Runtime configuration, read once from environment variables."""

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Mode(StrEnum):
    MOCK = "mock"
    REAL = "real"


@dataclass(frozen=True)
class Settings:
    mode: Mode
    upstream_url: str
    api_key_file: Path
    upstream_timeout_seconds: float
    mock_latency_ms: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            mode=Mode(os.getenv("LLM_MODE", Mode.MOCK)),
            upstream_url=os.getenv("UPSTREAM_URL", "https://api.anthropic.com"),
            api_key_file=Path(os.getenv("ANTHROPIC_API_KEY_FILE", "/var/run/secrets/anthropic/api-key")),
            upstream_timeout_seconds=float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "120")),
            mock_latency_ms=int(os.getenv("MOCK_LATENCY_MS", "400")),
        )
