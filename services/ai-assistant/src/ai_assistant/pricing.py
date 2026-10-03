"""Converts token usage to dollars."""

from dataclasses import dataclass

TOKENS_PER_MILLION = 1_000_000


@dataclass(frozen=True)
class Pricing:
    input_usd_per_million_tokens: float
    output_usd_per_million_tokens: float

    def cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * self.input_usd_per_million_tokens
            + output_tokens * self.output_usd_per_million_tokens
        ) / TOKENS_PER_MILLION
