"""Prometheus metrics exposed on /metrics.

LLM metrics follow the OpenTelemetry GenAI semantic conventions
(gen_ai.client.operation.duration, gen_ai.client.token.usage) in their Prometheus form:
dots become underscores, and the unit becomes a suffix.
"""

from prometheus_client import Counter, Gauge, Histogram

# Values of the gen_ai.* attributes used by this service.
GEN_AI_OPERATION_CHAT = "chat"
GEN_AI_SYSTEM_ANTHROPIC = "anthropic"
GEN_AI_LABELS = ["gen_ai_operation_name", "gen_ai_system", "gen_ai_request_model"]

# Bucket boundaries recommended by the OpenTelemetry GenAI semantic conventions.
GEN_AI_DURATION_BUCKETS = (0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64, 1.28, 2.56, 5.12, 10.24, 20.48, 40.96, 81.92)
GEN_AI_TOKEN_BUCKETS = (1, 4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144, 1048576)

CHAT_REQUESTS = Counter(
    "ai_assistant_chat_requests_total",
    "Chat requests by outcome.",
    ["outcome"],
)
CHAT_DURATION = Histogram(
    "ai_assistant_chat_duration_seconds",
    "Time to answer a chat request, including all LLM and tool calls, by outcome.",
    ["outcome"],
    buckets=(0.5, 1, 2.5, 5, 10, 20, 30, 60, 120),
)
CHATS_IN_PROGRESS = Gauge(
    "ai_assistant_chat_requests_in_progress",
    "Chat requests being answered right now (saturation signal).",
)
AGENT_STEPS = Histogram(
    "ai_assistant_agent_steps",
    "LLM calls needed to answer one chat request.",
    buckets=(1, 2, 3, 4, 5, 8, 10),
)
LLM_OPERATION_DURATION = Histogram(
    "gen_ai_client_operation_duration",
    "Duration of one LLM call, including SDK retries. error_type is set only when the call failed.",
    [*GEN_AI_LABELS, "error_type"],
    unit="seconds",
    buckets=GEN_AI_DURATION_BUCKETS,
)
LLM_TOKEN_USAGE = Histogram(
    "gen_ai_client_token_usage",
    "Tokens used by one LLM call, by token type (input or output).",
    [*GEN_AI_LABELS, "gen_ai_token_type"],
    buckets=GEN_AI_TOKEN_BUCKETS,
)
LLM_COST = Counter(
    "ai_assistant_llm_cost_usd_total",
    "Estimated LLM spend in US dollars.",
    ["gen_ai_request_model"],
)
TOOL_CALL_DURATION = Histogram(
    "ai_assistant_tool_call_duration_seconds",
    "Duration of one tool call, by tool and outcome.",
    ["tool", "outcome"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
