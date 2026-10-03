"""Runtime configuration, read once from environment variables."""

import os
from dataclasses import dataclass

# The real API key lives only in llm-gateway; the assistant sends this placeholder.
GATEWAY_API_KEY_PLACEHOLDER = "set-by-llm-gateway"


@dataclass(frozen=True)
class Settings:
    llm_gateway_url: str
    catalog_url: str
    model: str
    max_output_tokens: int
    max_agent_steps: int
    llm_max_retries: int
    llm_timeout_seconds: float
    catalog_timeout_seconds: float
    input_usd_per_million_tokens: float
    output_usd_per_million_tokens: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            llm_gateway_url=os.getenv("LLM_GATEWAY_URL", "http://llm-gateway"),
            catalog_url=os.getenv("CATALOG_URL", "http://catalog.retail-store.svc"),
            model=os.getenv("LLM_MODEL", "claude-haiku-4-5"),
            max_output_tokens=int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "1024")),
            max_agent_steps=int(os.getenv("LLM_MAX_AGENT_STEPS", "5")),
            llm_max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
            llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
            catalog_timeout_seconds=float(os.getenv("CATALOG_TIMEOUT_SECONDS", "5")),
            # Defaults: Claude Haiku 4.5 list prices.
            input_usd_per_million_tokens=float(os.getenv("LLM_INPUT_USD_PER_MTOK", "1.0")),
            output_usd_per_million_tokens=float(os.getenv("LLM_OUTPUT_USD_PER_MTOK", "5.0")),
        )
