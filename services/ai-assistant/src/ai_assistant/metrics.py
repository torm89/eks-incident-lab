"""Prometheus metrics exposed on /metrics."""

from prometheus_client import Counter, Histogram

CHAT_REQUESTS = Counter(
    "ai_assistant_chat_requests_total",
    "Chat requests by outcome.",
    ["outcome"],
)
CHAT_DURATION = Histogram(
    "ai_assistant_chat_duration_seconds",
    "Time to answer a chat request, including all LLM and tool calls.",
    buckets=(0.5, 1, 2.5, 5, 10, 20, 30, 60, 120),
)
AGENT_STEPS = Histogram(
    "ai_assistant_agent_steps",
    "LLM calls needed to answer one chat request.",
    buckets=(1, 2, 3, 4, 5, 8, 10),
)
LLM_CALLS = Counter(
    "ai_assistant_llm_calls_total",
    "LLM calls by outcome: success, HTTP status code, timeout or connection.",
    ["outcome"],
)
LLM_CALL_DURATION = Histogram(
    "ai_assistant_llm_call_duration_seconds",
    "Duration of one LLM call, including SDK retries.",
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 30, 60),
)
LLM_TOKENS = Counter(
    "ai_assistant_llm_tokens_total",
    "Tokens used, by direction (input or output).",
    ["direction"],
)
LLM_COST = Counter(
    "ai_assistant_llm_cost_usd_total",
    "Estimated LLM spend in US dollars.",
)
TOOL_CALLS = Counter(
    "ai_assistant_tool_calls_total",
    "Tool calls by tool and outcome.",
    ["tool", "outcome"],
)
