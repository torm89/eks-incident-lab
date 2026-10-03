"""Generate the Prometheus alerting rules in platform/monitoring/alerts/.

Alerts are code: edit this file or slo_definitions.py, run it, test and commit the YAML.

    uv run scripts/generate_alerts.py
    uv run scripts/test_alerts.py

Hybrid approach:
- Symptoms (what customers feel): SLOs with multiwindow, multi-burn-rate alerts, see slo_definitions.py.
- Causes (why it happens): plain thresholds, always severity "warning".
"""

from pathlib import Path
from typing import Any

import yaml

from slo_definitions import (
    BURN_RATE_ALERTS,
    MIN_EVENTS_IN_LONG_WINDOW,
    RECORDED_WINDOWS,
    SECONDS_PER_WINDOW,
    SLOS,
    BurnRateAlert,
    Slo,
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "platform" / "monitoring" / "alerts"
RUNBOOK_URL = "https://github.com/torm89/eks-incident-lab/blob/main/docs/runbooks/alerts.md"
LLM_HOURLY_BUDGET_USD = 3
DATA_STORE_PODS = ".*(mysql|postgresql|redis|rabbitmq|dynamodb).*"
APP_NAMESPACES = "retail-store|ai-assistant"


def dashboard_path(service: str) -> str:
    # Dashboard uids equal service (and namespace) names, see generate_dashboards.py.
    return f"/d/{service}"


def error_ratio_record(window: str) -> str:
    return f"slo:sli_error:ratio_rate{window}"


def requests_record(window: str) -> str:
    return f"slo:sli_requests:rate{window}"


# ---------------------------------------------------------------- SLO rules

def recording_rules(slo: Slo) -> list[dict[str, Any]]:
    rules = []
    for window in RECORDED_WINDOWS:
        labels = {"slo": slo.name, "service": slo.service}
        rules.append({"record": requests_record(window), "expr": slo.total(window), "labels": labels})
        rules.append({"record": error_ratio_record(window),
                      "expr": f"({slo.bad(window)}) / ({slo.total(window)})", "labels": labels})
    return rules


def burn_rate_alert(slo: Slo, alert: BurnRateAlert) -> dict[str, Any]:
    selector = f'{{slo="{slo.name}"}}'
    threshold = slo.error_ratio_threshold(alert)
    min_rate = MIN_EVENTS_IN_LONG_WINDOW / SECONDS_PER_WINDOW[alert.long_window]
    expr = (
        f"{error_ratio_record(alert.long_window)}{selector} > {threshold}\n"
        f"and {error_ratio_record(alert.short_window)}{selector} > {threshold}\n"
        f"and {requests_record(alert.long_window)}{selector} >= {round(min_rate, 6)}"
    )
    return {
        "alert": f"{slo.alert_prefix}{alert.suffix}",
        "expr": expr,
        "labels": {"severity": alert.severity, "slo": slo.name, "service": slo.service},
        "annotations": {
            "summary": f"{slo.title}: {alert.meaning}.",
            "description": (
                f"SLO: {slo.objective:.0%} of events are good ({slo.good_event}). "
                f"Over the last {alert.long_window} and {alert.short_window}, more than {threshold:.1%} of events were bad "
                f"(burn rate > {alert.burn_rate}x). Current {alert.long_window} error ratio: "
                "{{ $value | humanizePercentage }}."
            ),
            "runbook_url": f"{RUNBOOK_URL}#{slo.name}",
            "dashboard": dashboard_path(slo.service),
        },
    }


def slo_rule_groups() -> list[dict[str, Any]]:
    return [
        {"name": "slo-recordings", "interval": "15s",
         "rules": [rule for slo in SLOS for rule in recording_rules(slo)]},
        {"name": "slo-burn-rate-alerts",
         "rules": [burn_rate_alert(slo, alert) for slo in SLOS for alert in BURN_RATE_ALERTS]},
    ]


# ---------------------------------------------------------------- cause rules

def cause_alert(name: str, service: str, expr: str, duration: str, summary: str, description: str) -> dict[str, Any]:
    return {
        "alert": name,
        "expr": expr,
        "for": duration,
        "labels": {"severity": "warning", "service": service},
        "annotations": {"summary": summary, "description": description,
                        "runbook_url": f"{RUNBOOK_URL}#{name.lower()}",
                        "dashboard": dashboard_path(service)},
    }


def cause_rule_groups() -> list[dict[str, Any]]:
    gen_ai_calls = "sum(rate(gen_ai_client_operation_duration_seconds_count[5m]))"
    return [{"name": "cause-alerts", "rules": [
        cause_alert(
            "DataStoreNotReady", "retail-store",
            f'max by (namespace, pod) (kube_pod_status_ready{{namespace="retail-store", condition="true", pod=~"{DATA_STORE_PODS}"}}) == 0',
            "1m", "Data store pod {{ $labels.pod }} is not ready.",
            "A database, cache or queue of the store is down. Services that depend on it fail or lose data.",
        ),
        cause_alert(
            "PodMemoryNearLimit", "{{ $labels.namespace }}",
            f'sum by (namespace, pod) (container_memory_working_set_bytes{{namespace=~"{APP_NAMESPACES}", container!=""}})\n'
            f'/ sum by (namespace, pod) (kube_pod_container_resource_limits{{namespace=~"{APP_NAMESPACES}", resource="memory"}}) > 0.9',
            "5m", "Pod {{ $labels.pod }} uses {{ $value | humanizePercentage }} of its memory limit.",
            "At 100% the container is OOM-killed and restarted.",
        ),
        cause_alert(
            "LlmRetryAmplification", "ai-assistant",
            f"sum(rate(llm_gateway_requests_total[5m])) / {gen_ai_calls} > 1.5\nand {gen_ai_calls} * 300 >= {MIN_EVENTS_IN_LONG_WINDOW}",
            "2m", "The LLM API gets {{ $value | humanize }} requests per LLM call.",
            "SDK retries multiply the load: the LLM API is rate limited or failing (429, 529, 5xx, timeouts).",
        ),
        cause_alert(
            "LlmCostBudgetExceeded", "ai-assistant",
            f"sum(rate(ai_assistant_llm_cost_usd_total[15m])) * 3600 > {LLM_HOURLY_BUDGET_USD}",
            "5m", "LLM spend is {{ $value | humanize }} USD per hour (budget: " + str(LLM_HOURLY_BUDGET_USD) + " USD).",
            "More traffic, longer prompts or a looping agent. In mock mode this is the cost the real API would have.",
        ),
    ]}]


# ---------------------------------------------------------------- output

def prometheus_rule(name: str, groups: list[dict[str, Any]]) -> dict[str, Any]:
    return {"apiVersion": "monitoring.coreos.com/v1", "kind": "PrometheusRule",
            "metadata": {"name": name, "namespace": "monitoring"}, "spec": {"groups": groups}}


class _LiteralDumper(yaml.SafeDumper):
    """Readable output: multi-line strings (PromQL) as | blocks, no anchors, no line wrapping."""

    def ignore_aliases(self, data: Any) -> bool:
        return True


_LiteralDumper.add_representer(
    str, lambda dumper, value: dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|" if "\n" in value else None)
)


def main() -> None:
    header = "# Generated by scripts/generate_alerts.py. Do not edit by hand.\n"
    for name, groups in (("slo-rules", slo_rule_groups()), ("cause-rules", cause_rule_groups())):
        path = OUTPUT_DIR / f"{name}.yaml"
        body = yaml.dump(prometheus_rule(name, groups), Dumper=_LiteralDumper, sort_keys=False, width=1_000_000)
        path.write_text(header + body, encoding="utf-8", newline="\n")
        print(f"Wrote {path.relative_to(OUTPUT_DIR.parent.parent.parent)}")


if __name__ == "__main__":
    main()
