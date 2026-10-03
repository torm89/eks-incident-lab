"""Agent loop: Claude answers a customer question, calling catalog tools as needed.

A manual loop (instead of the SDK tool runner) so every LLM call is measured on its own
and the number of steps has a hard limit.
"""

import time
from dataclasses import dataclass
from typing import Any

import anthropic

from ai_assistant.metrics import (
    GEN_AI_OPERATION_CHAT,
    GEN_AI_SYSTEM_ANTHROPIC,
    LLM_COST,
    LLM_OPERATION_DURATION,
    LLM_TOKEN_USAGE,
)
from ai_assistant.pricing import Pricing
from ai_assistant.tools import TOOL_DEFINITIONS, ToolExecutor

SYSTEM_PROMPT = (
    "You are the shopping assistant of an online retail store. "
    "Answer customer questions about the products the store sells. "
    "Always look products up with the tools; never invent products, prices or details. "
    "Keep answers short: a few sentences or a short list with names and prices."
)


class AgentError(Exception):
    """The agent could not produce an answer."""


class LlmUnavailableError(AgentError):
    pass


class MaxStepsExceededError(AgentError):
    pass


@dataclass(frozen=True)
class Answer:
    text: str
    steps: int


class ShoppingAgent:
    def __init__(
        self,
        client: anthropic.Anthropic,
        tools: ToolExecutor,
        pricing: Pricing,
        model: str,
        max_output_tokens: int,
        max_steps: int,
    ) -> None:
        self._client = client
        self._tools = tools
        self._pricing = pricing
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._max_steps = max_steps

    def answer(self, question: str) -> Answer:
        messages: list[dict[str, Any]] = [{"role": "user", "content": question}]
        for step in range(1, self._max_steps + 1):
            response = self._call_llm(messages)
            if response.stop_reason != "tool_use":
                return Answer(text=_text_of(response), steps=step)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": self._run_tools(response)})
        raise MaxStepsExceededError(f"No answer after {self._max_steps} LLM calls")

    def _call_llm(self, messages: list[dict[str, Any]]) -> anthropic.types.Message:
        started = time.perf_counter()
        error_type = ""  # OpenTelemetry error.type: set only when the call failed.
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_output_tokens,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )
        except anthropic.APIStatusError as error:
            error_type = str(error.status_code)
            raise LlmUnavailableError(f"LLM returned HTTP {error.status_code}") from error
        except anthropic.APITimeoutError as error:
            error_type = "timeout"
            raise LlmUnavailableError("LLM call timed out") from error
        except anthropic.APIConnectionError as error:
            error_type = "connection"
            raise LlmUnavailableError("Cannot reach the LLM") from error
        finally:
            LLM_OPERATION_DURATION.labels(**self._gen_ai_labels(), error_type=error_type).observe(
                time.perf_counter() - started
            )

        self._record_usage(response.usage)
        return response

    def _gen_ai_labels(self) -> dict[str, str]:
        return {
            "gen_ai_operation_name": GEN_AI_OPERATION_CHAT,
            "gen_ai_system": GEN_AI_SYSTEM_ANTHROPIC,
            "gen_ai_request_model": self._model,
        }

    def _record_usage(self, usage: anthropic.types.Usage) -> None:
        LLM_TOKEN_USAGE.labels(**self._gen_ai_labels(), gen_ai_token_type="input").observe(usage.input_tokens)
        LLM_TOKEN_USAGE.labels(**self._gen_ai_labels(), gen_ai_token_type="output").observe(usage.output_tokens)
        LLM_COST.labels(gen_ai_request_model=self._model).inc(
            self._pricing.cost_usd(usage.input_tokens, usage.output_tokens)
        )

    def _run_tools(self, response: anthropic.types.Message) -> list[dict[str, Any]]:
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result = self._tools.run(block.name, block.input)
            results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": result.content, "is_error": result.is_error}
            )
        return results


def _text_of(response: anthropic.types.Message) -> str:
    return "\n".join(block.text for block in response.content if block.type == "text")
