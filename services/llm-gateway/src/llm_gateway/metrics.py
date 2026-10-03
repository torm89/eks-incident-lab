"""Prometheus metrics exposed on /metrics."""

from prometheus_client import Counter, Histogram

REQUESTS = Counter(
    "llm_gateway_requests_total",
    "Messages API requests handled by the gateway.",
    ["mode", "status"],
)
REQUEST_DURATION = Histogram(
    "llm_gateway_request_duration_seconds",
    "Time to answer a Messages API request, including injected latency.",
    ["mode"],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 30, 60, 120),
)
INJECTED_FAULTS = Counter(
    "llm_gateway_injected_faults_total",
    "Requests affected by an injected fault.",
    ["fault"],
)
