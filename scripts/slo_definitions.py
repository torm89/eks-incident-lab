"""Service level objectives of the lab, shared by generate_alerts.py and generate_dashboards.py.

Alerting follows the multiwindow, multi-burn-rate method of the Google SRE workbook
(https://sre.google/workbook/alerting-on-slos/), with every window scaled down 12x so alerts
fire within minutes and fit a 1-2 hour practice session:

    alert         burn rate   Google windows (30-day SLO)   lab windows
    fast (page)   14.4x       1h and 5m                     5m and 1m
    slow (ticket)  6x         6h and 30m                    30m and 5m

Burn rate = error ratio / error budget. It does not depend on the SLO period, only the windows do.
"""

from dataclasses import dataclass

# Window lengths used by recording rules; 1m is the shortest that works with a 15s scrape interval.
RECORDED_WINDOWS = ("1m", "5m", "30m")
SECONDS_PER_WINDOW = {"1m": 60, "5m": 300, "30m": 1800}

# Ignore bursts of errors when there is almost no traffic: one failed request out of three
# is a 33% error ratio, but not an incident (SRE workbook: "low-traffic services").
MIN_EVENTS_IN_LONG_WINDOW = 10


@dataclass(frozen=True)
class BurnRateAlert:
    suffix: str
    severity: str
    burn_rate: float
    long_window: str
    short_window: str
    meaning: str


FAST_BURN = BurnRateAlert("BudgetBurnFast", "critical", 14.4, "5m", "1m",
                          "error budget burns 14.4x faster than sustainable: act now")
SLOW_BURN = BurnRateAlert("BudgetBurnSlow", "warning", 6, "30m", "5m",
                          "error budget burns 6x faster than sustainable: look at it soon")
BURN_RATE_ALERTS = (FAST_BURN, SLOW_BURN)


@dataclass(frozen=True)
class Slo:
    name: str
    service: str
    title: str
    objective: float
    good_event: str
    # PromQL with a literal {window} placeholder (not str.format: PromQL has braces), e.g. [{window}] -> [5m].
    total_query: str
    bad_query: str

    @property
    def error_budget(self) -> float:
        return round(1 - self.objective, 6)

    @property
    def alert_prefix(self) -> str:
        return "".join(part.capitalize() for part in self.name.split("-"))

    def total(self, window: str) -> str:
        return self.total_query.replace("{window}", window)

    def bad(self, window: str) -> str:
        return self.bad_query.replace("{window}", window)

    def error_ratio_threshold(self, alert: BurnRateAlert) -> float:
        return round(alert.burn_rate * self.error_budget, 6)


def _availability(metric: str, selector: str, bad_selector: str) -> tuple[str, str]:
    total = f"sum(rate({metric}{{{selector}}}[{{window}}]))"
    bad = f"sum(rate({metric}{{{selector}, {bad_selector}}}[{{window}}]))"
    return total, bad


def _latency(histogram: str, selector: str, threshold_le: str) -> tuple[str, str]:
    total = f"sum(rate({histogram}_count{{{selector}}}[{{window}}]))"
    fast = f'sum(rate({histogram}_bucket{{{selector}, le="{threshold_le}"}}[{{window}}]))'
    return total, f"({total} - {fast})"


STORE_UI = 'namespace="retail-store", app_kubernetes_io_name="ui", uri!~"/actuator.*"'

SLOS = (
    Slo("store-availability", "retail-store", "Store availability", 0.99,
        "UI request without a 5xx status",
        *_availability("http_server_requests_seconds_count", STORE_UI, 'status=~"5.."')),
    Slo("store-latency", "retail-store", "Store latency", 0.95,
        "UI request faster than 1 s",
        *_latency("http_server_requests_seconds", STORE_UI, "1.0")),
    Slo("assistant-availability", "ai-assistant", "Assistant availability", 0.95,
        "question answered (no LLM error, no step limit)",
        *_availability("ai_assistant_chat_requests_total", 'namespace="ai-assistant"', 'outcome!="success"')),
    Slo("assistant-latency", "ai-assistant", "Assistant latency", 0.95,
        "question answered within 30 s",
        *_latency("ai_assistant_chat_duration_seconds", 'namespace="ai-assistant"', "30.0")),
    Slo("assistant-tool-quality", "ai-assistant", "Assistant tool quality", 0.95,
        "tool call that returned data, not an error (catches HTTP 200 answers built on failed tools)",
        *_availability("ai_assistant_tool_call_duration_seconds_count", 'namespace="ai-assistant"', 'outcome!="success"')),
)


def slos_for(service: str) -> list[Slo]:
    return [slo for slo in SLOS if slo.service == service]


def _validate() -> None:
    for slo in SLOS:
        for alert in BURN_RATE_ALERTS:
            # A burn rate needing an error ratio above 100% could never fire.
            if slo.error_ratio_threshold(alert) >= 1:
                raise ValueError(f"{slo.name}: {alert.suffix} needs more than 100% errors; lower the objective's burn rate")


_validate()
