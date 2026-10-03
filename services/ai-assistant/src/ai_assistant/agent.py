"""Agent loop: Claude answers a customer question, calling catalog tools as needed.

A manual loop (instead of the SDK tool runner) so every LLM call is measured on its own
and the number of steps has a hard limit.
"""

import time
from dataclasses import dataclass
from typing import Any

import anthropic

from ai_assistant.metrics import LLM_CALL_DURATION, LLM_CALLS, LLM_COST, LLM_TOKENS
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
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_output_tokens,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )
        except anthropic.APIStatusError as error:
            LLM_CALLS.labels(outcome=str(error.status_code)).inc()
            raise LlmUnavailableError(f"LLM returned HTTP {error.status_code}") from error
        except anthropic.APITimeoutError as error:
            LLM_CALLS.labels(outcome="timeout").inc()
            raise LlmUnavailableError("LLM call timed out") from error
        except anthropic.APIConnectionError as error:
            LLM_CALLS.labels(outcome="connection").inc()
            raise LlmUnavailableError("Cannot reach the LLM") from error
        finally:
            LLM_CALL_DURATION.observe(time.perf_counter() - started)

        LLM_CALLS.labels(outcome="success").inc()
        self._record_usage(response.usage)
        return response

    def _record_usage(self, usage: anthropic.types.Usage) -> None:
        LLM_TOKENS.labels(direction="input").inc(usage.input_tokens)
        LLM_TOKENS.labels(direction="output").inc(usage.output_tokens)
        LLM_COST.inc(self._pricing.cost_usd(usage.input_tokens, usage.output_tokens))

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
