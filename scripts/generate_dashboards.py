"""Generate the Grafana dashboards in platform/monitoring/dashboards/.

Dashboards are code: edit this file, run it, commit the JSON. Do not edit dashboards in the browser.

    uv run scripts/generate_dashboards.py

Design follows common practice:
- Golden signals (traffic, errors, latency, saturation) in the top row, details below (RED per service, USE for resources).
- Percentiles from histograms, never averages; latency split by outcome so fast failures do not hide slow successes.
- Every panel has a description and a unit; stats and key graphs have thresholds.
- $__rate_interval in every rate(), a datasource variable, shared crosshair, links between the lab dashboards.
- An SLO row: error budget left in the session and burn rate, the same SLOs as the alerts (slo_definitions.py).
- Annotations mark firing alerts and rollouts. Chaos injection/recovery markers exist but are off by default
  (realistic practice); switch them on for the review.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from slo_definitions import FAST_BURN, SLOW_BURN, slos_for

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "platform" / "monitoring" / "dashboards"
LAB_TAG = "eks-incident-lab"
# Common title prefix, so the lab dashboards sit next to each other in the alphabetical list
# (same "Group / Name" style as the built-in "Kubernetes / ..." dashboards).
TITLE_PREFIX = "Incident Lab / "
DATASOURCE = {"type": "prometheus", "uid": "${datasource}"}
RATE = "[$__rate_interval]"
GRID_WIDTH = 24
STAT_HEIGHT = 4
GRAPH_HEIGHT = 8
AXIS_HEADROOM = 1.25  # graphs with thresholds show at least 0..125% of the highest threshold

# Threshold steps: (color, from value). The first step starts at minus infinity.
LOWER_IS_BETTER_RATIO = [("green", None), ("yellow", 0.01), ("red", 0.05)]
HIGHER_IS_BETTER_RATIO = [("red", None), ("yellow", 0.75), ("green", 1)]


# ---------------------------------------------------------------- panel builders

def target(expr: str, legend: str = "", ref: str = "A") -> dict[str, Any]:
    return {"datasource": DATASOURCE, "expr": expr, "legendFormat": legend, "refId": ref}


def targets(*queries: tuple[str, str]) -> list[dict[str, Any]]:
    return [target(expr, legend, chr(ord("A") + index)) for index, (expr, legend) in enumerate(queries)]


def thresholds(steps: list[tuple[str, float | None]]) -> dict[str, Any]:
    return {"mode": "absolute", "steps": [{"color": color, "value": value} for color, value in steps]}


@dataclass
class Panel:
    title: str
    description: str
    queries: list[dict[str, Any]]
    unit: str
    kind: str = "timeseries"
    width: int = 12
    height: int = GRAPH_HEIGHT
    steps: list[tuple[str, float | None]] | None = None
    options: dict[str, Any] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)

    def to_json(self, panel_id: int, x: int, y: int) -> dict[str, Any]:
        defaults: dict[str, Any] = {"unit": self.unit, **self.defaults}
        if self.steps:
            defaults["thresholds"] = thresholds(self.steps)
            if self.kind == "timeseries":
                # Soft axis range up to just above the highest threshold: a healthy all-zero graph stays
                # readable (Grafana would otherwise pick e.g. 0-100 = 10000%) and the threshold line stays visible.
                highest_threshold = max(value for _, value in self.steps if value is not None)
                defaults["custom"] = {"thresholdsStyle": {"mode": "line+area"},
                                      "axisSoftMin": 0, "axisSoftMax": highest_threshold * AXIS_HEADROOM}
            else:
                defaults["color"] = {"mode": "thresholds"}
        return {
            "id": panel_id,
            "type": self.kind,
            "title": self.title,
            "description": self.description,
            "datasource": DATASOURCE,
            "gridPos": {"x": x, "y": y, "w": self.width, "h": self.height},
            "fieldConfig": {"defaults": defaults, "overrides": []},
            "options": self.options or _default_options(self.kind),
            "targets": self.queries,
        }


def _default_options(kind: str) -> dict[str, Any]:
    if kind == "stat":
        return {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                "colorMode": "background", "graphMode": "area", "textMode": "value"}
    if kind == "state-timeline":
        return {"showValue": "never", "mergeValues": True, "rowHeight": 0.8, "legend": {"showLegend": False}}
    return {"legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
            "tooltip": {"mode": "multi", "sort": "desc"}}


def stat(title: str, description: str, expr: str, unit: str, steps=None, width: int = 6) -> Panel:
    return Panel(title, description, [target(expr)], unit, kind="stat", width=width, height=STAT_HEIGHT, steps=steps)


def graph(title: str, description: str, queries: list[dict[str, Any]], unit: str, steps=None, width: int = 12) -> Panel:
    return Panel(title, description, queries, unit, width=width, steps=steps)


def ready_timeline(title: str, description: str, expr: str, legend: str) -> Panel:
    mappings = [{"type": "value", "options": {"0": {"text": "Not ready", "color": "red"},
                                              "1": {"text": "Ready", "color": "green"}}}]
    return Panel(title, description, [target(expr, legend)], "none", kind="state-timeline",
                 width=GRID_WIDTH, defaults={"mappings": mappings, "color": {"mode": "thresholds"}})


@dataclass
class Row:
    title: str
    panels: list[Panel]


# ---------------------------------------------------------------- dashboard builder

def layout(rows: list[Row]) -> list[dict[str, Any]]:
    """Places rows top to bottom and panels left to right, wrapping at the grid width."""
    result, panel_id, y = [], 1, 0
    for row in rows:
        result.append({"id": panel_id, "type": "row", "title": row.title, "collapsed": False,
                       "gridPos": {"x": 0, "y": y, "w": GRID_WIDTH, "h": 1}, "panels": []})
        panel_id, y, x, line_height = panel_id + 1, y + 1, 0, 0
        for panel in row.panels:
            if x + panel.width > GRID_WIDTH:
                x, y, line_height = 0, y + line_height, 0
            result.append(panel.to_json(panel_id, x, y))
            panel_id, x, line_height = panel_id + 1, x + panel.width, max(line_height, panel.height)
        y += line_height
    return result


def datasource_variable() -> dict[str, Any]:
    return {"name": "datasource", "label": "Data source", "type": "datasource", "query": "prometheus",
            "current": {"text": "Prometheus", "value": "prometheus"}, "hide": 0}


def query_variable(name: str, label: str, query: str, default: str, include_all: bool = False) -> dict[str, Any]:
    variable = {"name": name, "label": label, "type": "query", "datasource": DATASOURCE,
                "query": {"query": query, "refId": name}, "refresh": 2, "sort": 1,
                "current": {"text": default, "value": default}, "hide": 0}
    if include_all:
        variable.update({"includeAll": True, "allValue": ".*"})
    return variable


def annotations(namespace: str, service: str) -> list[dict[str, Any]]:
    def prometheus_annotation(name: str, expr: str, title: str, color: str, use_value_for_time: bool,
                              enabled: bool = True) -> dict[str, Any]:
        return {"name": name, "datasource": DATASOURCE, "enable": enabled, "iconColor": color, "expr": expr,
                "titleFormat": title, "step": "30s", "useValueForTime": use_value_for_time}

    builtin = {"builtIn": 1, "datasource": {"type": "grafana", "uid": "-- Grafana --"}, "enable": True,
               "hide": True, "iconColor": "rgba(0, 211, 255, 1)", "name": "Annotations & Alerts", "type": "dashboard"}
    # Chaos Jobs from chaos/base are named <scenario>-inject-... and <scenario>-recover-...
    job_start = 'max by (job_name) (kube_job_status_start_time{{job_name=~".*-{step}-.*"}}) * 1000'
    return [
        builtin,
        # Off by default: a real incident has no "chaos injected" marker. Practice blind, then switch
        # them on for the review to measure time to detect (inject -> "Alerts firing").
        prometheus_annotation("Chaos injected", job_start.format(step="inject"), "Chaos: {{job_name}}", "red", True, enabled=False),
        prometheus_annotation("Chaos recovered", job_start.format(step="recover"), "Recover: {{job_name}}", "green", True, enabled=False),
        prometheus_annotation(
            "Alerts firing",
            f'ALERTS{{alertstate="firing", service="{service}"}} or ALERTS{{alertstate="firing", namespace="{namespace}"}}',
            "{{alertname}} ({{severity}})", "orange", False,
        ),
        prometheus_annotation(
            "Rollouts",
            f'changes(kube_deployment_status_observed_generation{{namespace="{namespace}"}}[1m]) > 0',
            "Rollout: {{deployment}}", "blue", False,
        ),
    ]


def dashboard(uid: str, title: str, description: str, namespace: str,
              variables: list[dict[str, Any]], rows: list[Row]) -> dict[str, Any]:
    return {
        "uid": uid,
        "title": TITLE_PREFIX + title,
        "description": description,
        "tags": [LAB_TAG],
        "timezone": "browser",
        "refresh": "30s",
        "time": {"from": "now-30m", "to": "now"},
        "graphTooltip": 1,
        "schemaVersion": 39,
        "editable": True,
        "links": [{"title": "Lab dashboards", "type": "dashboards", "tags": [LAB_TAG], "asDropdown": True,
                   "includeVars": False, "keepTime": True}],
        "annotations": {"list": annotations(namespace, uid)},
        "templating": {"list": [datasource_variable(), *variables]},
        "panels": layout(rows),
    }


# ---------------------------------------------------------------- shared queries

def histogram_quantile(quantile: float, bucket_metric: str, selector: str, by: str = "") -> str:
    group = f"{by}, le" if by else "le"
    return f"histogram_quantile({quantile}, sum by ({group}) (rate({bucket_metric}{{{selector}}}{RATE})))"


def error_ratio_by(counter: str, selector: str, bad_selector: str, by: str) -> str:
    """Bad / total per group, 0 (not empty) for groups without failures."""
    total = f"sum by ({by}) (rate({counter}{{{selector}}}{RATE}))"
    return f"(sum by ({by}) (rate({counter}{{{selector}, {bad_selector}}}{RATE})) or {total} * 0) / {total}"


def saturation_panels(namespace: str) -> list[Panel]:
    ns = f'namespace="{namespace}", container!=""'
    return [
        graph("CPU by pod", "CPU cores used by each pod.",
              [target(f"sum by (pod) (rate(container_cpu_usage_seconds_total{{{ns}}}{RATE}))", "{{pod}}")], "short", width=8),
        graph("Memory, % of limit", "Working set memory as a share of the memory limit. At 100% the container is OOM-killed.",
              [target(f'sum by (pod) (container_memory_working_set_bytes{{{ns}}}) / sum by (pod) '
                      f'(kube_pod_container_resource_limits{{namespace="{namespace}", resource="memory"}})', "{{pod}}")],
              "percentunit", steps=[("green", None), ("yellow", 0.8), ("red", 0.95)], width=8),
        graph("Container restarts (15 min)", "Restarts in the last 15 minutes: crashes, OOM kills or failed liveness probes.",
              [target(f'sum by (pod) (increase(kube_pod_container_status_restarts_total{{namespace="{namespace}"}}[15m]))',
                      "{{pod}}")], "none", width=8),
    ]


def slo_row(service: str) -> Row:
    """Error budget left in the selected time range (one session) and burn rate per SLO."""
    slos = slos_for(service)
    stat_width = (GRID_WIDTH // 2) // len(slos)
    budget_left = [
        stat(f"{slo.title}: budget left", f"SLO {slo.objective:.0%}: {slo.good_event}. "
             "Share of the error budget still unused in the selected time range. Below 0: SLO missed.",
             f'1 - (({slo.bad("$__range")}) / ({slo.total("$__range")})) / {slo.error_budget}',
             "percentunit", [("red", None), ("yellow", 0.25), ("green", 0.5)], width=stat_width)
        for slo in slos
    ]
    burn_rate = graph(
        "Burn rate (5m window)",
        f"How fast each SLO uses its error budget. 1 = sustainable. Alerts: >{SLOW_BURN.burn_rate}x warning, "
        f">{FAST_BURN.burn_rate}x critical (both also need a second window to agree).",
        targets(*[(f'slo:sli_error:ratio_rate5m{{slo="{slo.name}"}} / {slo.error_budget}', slo.title) for slo in slos]),
        "none", steps=[("green", None), ("yellow", SLOW_BURN.burn_rate), ("red", FAST_BURN.burn_rate)], width=GRID_WIDTH // 2,
    )
    return Row("SLOs and error budget", [*budget_left, burn_rate])


# ---------------------------------------------------------------- Retail Store

def retail_store() -> dict[str, Any]:
    ns = 'namespace="$namespace"'
    java = f'{ns}, uri!~"/actuator.*"'  # skip health checks and metric scrapes
    go = f'{ns}, url!~"/health.*|/metrics.*"'
    ui = f'{java}, app_kubernetes_io_name="ui"'
    service = "app_kubernetes_io_name"
    pods_not_jobs = f'kube_pod_info{{{ns}, created_by_kind!="Job"}}'

    golden = Row("Golden signals: the store as customers see it (UI)", [
        stat("Traffic", "Requests per second entering the store through the UI.",
             f"sum(rate(http_server_requests_seconds_count{{{ui}}}{RATE}))", "reqps", width=5),
        stat("Errors", "Share of UI requests that end with a 5xx status.",
             f'(sum(rate(http_server_requests_seconds_count{{{ui}, status=~"5.."}}{RATE})) or vector(0)) / '
             f"sum(rate(http_server_requests_seconds_count{{{ui}}}{RATE}))",
             "percentunit", LOWER_IS_BETTER_RATIO, width=5),
        stat("Latency p95", "95% of successful UI requests are faster than this.",
             histogram_quantile(0.95, "http_server_requests_seconds_bucket", f'{ui}, outcome="SUCCESS"'),
             "s", [("green", None), ("yellow", 0.5), ("red", 1)], width=5),
        stat("Orders / min", "Business signal: orders placed per minute (orders service).",
             f'sum(rate(watch_orders_total{{{ns}, productId="*"}}{RATE})) * 60', "none",
             [("red", None), ("green", 0.1)], width=5),
        stat("Pods ready", "Share of the store's pods (without chaos Jobs) that are ready.",
             f'sum(kube_pod_status_ready{{{ns}, condition="true"}} * on (namespace, pod) group_left () {pods_not_jobs}) / '
             f"count({pods_not_jobs})",
             "percentunit", HIGHER_IS_BETTER_RATIO, width=4),
    ])

    red = Row("Services: rate, errors, duration", [
        graph("Requests / s by service", "Java services and catalog (Go). checkout exposes no HTTP metrics.",
              targets((f"sum by ({service}) (rate(http_server_requests_seconds_count{{{java}}}{RATE}))", f"{{{{{service}}}}}"),
                      (f"sum by ({service}) (rate(gin_requests_total{{{go}}}{RATE}))", f"{{{{{service}}}}}")),
              "reqps"),
        graph("Error ratio (5xx) by service", "Share of requests that fail, per service. Line: 5%.",
              targets((error_ratio_by("http_server_requests_seconds_count", java, 'status=~"5.."', service), f"{{{{{service}}}}}"),
                      (error_ratio_by("gin_requests_total", go, 'code=~"5.."', service), f"{{{{{service}}}}}")),
              "percentunit", steps=[("green", None), ("red", 0.05)]),
        graph("Latency by service", "p95 for the Java services. Catalog (Go) only exposes a summary, so it shows the average "
              "(including health checks). Catalog is often the root cause of a slow UI.",
              targets((histogram_quantile(0.95, "http_server_requests_seconds_bucket", java, by=service), f"{{{{{service}}}}} p95"),
                      (f"sum by ({service}) (rate(gin_request_duration_seconds_sum{{{ns}}}{RATE})) / "
                       f"sum by ({service}) (rate(gin_request_duration_seconds_count{{{ns}}}{RATE}))", f"{{{{{service}}}}} average")),
              "s", steps=[("green", None), ("red", 1)]),
        graph("UI latency: successful vs failed", "p50, p95 and p99 by outcome. Fast failures must not hide slow successes.",
              targets(*[(histogram_quantile(q, "http_server_requests_seconds_bucket", ui, by="outcome"), f"p{int(q * 100)} {{{{outcome}}}}")
                        for q in (0.5, 0.95, 0.99)]),
              "s"),
    ])

    saturation = Row("Saturation: pods and nodes", [
        *saturation_panels("$namespace"),
        graph("CPU, % of request", "CPU used vs the CPU the pod requested. The pods have no CPU limits (no throttling); "
              "above 100% a pod lives on spare node CPU, which disappears when another node fails.",
              [target(f'sum by (pod) (rate(container_cpu_usage_seconds_total{{{ns}, container!=""}}{RATE})) / '
                      f'sum by (pod) (kube_pod_container_resource_requests{{{ns}, resource="cpu"}})', "{{pod}}")],
              "percentunit", steps=[("green", None), ("red", 1)], width=8),
        graph("Node CPU and memory", "Utilization of each worker node. Losing a node moves its load to the others.",
              targets(("1 - avg by (instance) (rate(node_cpu_seconds_total{mode=\"idle\"}" + RATE + "))", "CPU {{instance}}"),
                      ("1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes", "memory {{instance}}")),
              "percentunit", steps=[("green", None), ("red", 0.9)], width=8),
        graph("Pods per node, % of max", "Running pods vs the node's pod limit (17 on t3.medium). A full node cannot take pods moved from a lost node.",
              [target('count by (node) (kube_pod_info{node!=""}) / sum by (node) (kube_node_status_allocatable{resource="pods"})',
                      "{{node}}")],
              "percentunit", steps=[("green", None), ("red", 0.9)], width=8),
    ])

    dependencies = Row("Dependencies: data stores", [
        ready_timeline("Data store pods", "Readiness history of MySQL, PostgreSQL, Redis, RabbitMQ and DynamoDB Local.",
                       f'max by (pod) (kube_pod_status_ready{{{ns}, condition="true", '
                       f'pod=~".*(mysql|postgresql|redis|rabbitmq|dynamodb).*"}})', "{{pod}}"),
    ])

    return dashboard(
        "retail-store", "Retail Store",
        "Golden signals, RED per service, saturation and data stores of the Retail Store Sample App.",
        "$namespace",
        [query_variable("namespace", "Namespace", "label_values(kube_pod_info, namespace)", "retail-store")],
        [golden, slo_row("retail-store"), red, saturation, dependencies],
    )


# ---------------------------------------------------------------- AI Assistant

def ai_assistant() -> dict[str, Any]:
    chat = "ai_assistant_chat_requests_total"
    model = 'gen_ai_request_model=~"$model"'
    llm_count = "gen_ai_client_operation_duration_seconds_count"
    succeeded = 'error_type=""'

    golden = Row("Golden signals: the assistant as customers see it", [
        stat("Traffic", "Chat questions per second.", f"sum(rate({chat}{RATE}))", "reqps", width=5),
        stat("Errors", "Share of questions without an answer (LLM errors, step limit). Answers built on failed tools still count as success.",
             f'(sum(rate({chat}{{outcome!="success"}}{RATE})) or vector(0)) / sum(rate({chat}{RATE}))',
             "percentunit", LOWER_IS_BETTER_RATIO, width=5),
        stat("Latency p95", "95% of answered questions are faster than this (all LLM and tool calls together).",
             histogram_quantile(0.95, "ai_assistant_chat_duration_seconds_bucket", 'outcome="success"'),
             "s", [("green", None), ("yellow", 10), ("red", 30)], width=5),
        stat("In progress", "Questions being answered right now. Growing means requests pile up (saturation).",
             "sum(ai_assistant_chat_requests_in_progress)", "none", [("green", None), ("yellow", 5), ("red", 10)], width=4),
        stat("LLM cost / hour", "Estimated from tokens and list prices. In mock mode: what the real API would cost.",
             f"sum(rate(ai_assistant_llm_cost_usd_total{{{model}}}{RATE})) * 3600", "currencyUSD",
             [("green", None), ("yellow", 1), ("red", 5)], width=5),
    ])

    chat_row = Row("Chat: rate, errors, duration", [
        graph("Questions / s by outcome", "success, llm_error (no answer from the LLM) or max_steps (agent loop limit).",
              [target(f"sum by (outcome) (rate({chat}{RATE}))", "{{outcome}}")], "reqps", width=6),
        graph("Latency p95 by outcome", "Answered vs failed questions. A slow LLM shows up in both.",
              [target(histogram_quantile(0.95, "ai_assistant_chat_duration_seconds_bucket", "", by="outcome"), "{{outcome}}")],
              "s", width=6),
        graph("Agent steps per answer", "LLM calls needed per answered question. A rise means the agent loops more.",
              [target("sum(rate(ai_assistant_agent_steps_sum" + RATE + ")) / sum(rate(ai_assistant_agent_steps_count" + RATE + "))",
                      "steps per answer")], "short", width=6),
        graph("Cost per answer", "Dollars of LLM spend per answered question.",
              [target(f"sum(rate(ai_assistant_llm_cost_usd_total{{{model}}}{RATE})) / "
                      f'sum(rate({chat}{{outcome="success"}}{RATE}))', "USD per answer")], "currencyUSD", width=6),
    ])

    llm = Row("LLM calls (OpenTelemetry GenAI metrics)", [
        graph("LLM calls / s by result", "One call can include SDK retries. error_type: HTTP status, timeout or connection.",
              [target(f'label_replace(sum by (error_type) (rate({llm_count}{{{model}}}{RATE})), "error_type", "success", "error_type", "")',
                      "{{error_type}}")], "reqps", width=8),
        graph("LLM latency (successful calls)", "p50, p95 and p99 of gen_ai.client.operation.duration.",
              targets(*[(histogram_quantile(q, "gen_ai_client_operation_duration_seconds_bucket", f"{model}, {succeeded}"),
                         f"p{int(q * 100)}") for q in (0.5, 0.95, 0.99)]),
              "s", width=8),
        graph("Retry amplification", "Requests the gateway receives per LLM call. 1 = no retries; 3 = every call retried twice.",
              [target(f"sum(rate(llm_gateway_requests_total{RATE})) / sum(rate({llm_count}{RATE}))", "gateway requests per LLM call")],
              "none", steps=[("green", None), ("red", 1.5)], width=8),
        graph("Tokens / min by type", "gen_ai.client.token.usage: input (prompt, tools, history) and output tokens.",
              [target(f"sum by (gen_ai_token_type) (rate(gen_ai_client_token_usage_sum{{{model}}}{RATE})) * 60",
                      "{{gen_ai_token_type}}")], "short"),
        graph("Tokens per call p95 by type", "Large input means long history or big tool results: cost and latency grow with it.",
              [target(histogram_quantile(0.95, "gen_ai_client_token_usage_bucket", model, by="gen_ai_token_type"),
                      "{{gen_ai_token_type}}")], "short"),
    ])

    tools = Row("Tools", [
        graph("Tool calls / s by tool and outcome", "error = the tool failed and Claude got an error result instead of data.",
              [target(f"sum by (tool, outcome) (rate(ai_assistant_tool_call_duration_seconds_count{RATE}))", "{{tool}} {{outcome}}")],
              "reqps"),
        graph("Tool latency p95 by tool", "Slow tools make slow answers, even when the LLM is fast.",
              [target(histogram_quantile(0.95, "ai_assistant_tool_call_duration_seconds_bucket", "", by="tool"), "{{tool}}")],
              "s", steps=[("green", None), ("red", 5)]),
    ])

    gateway = Row("LLM gateway", [
        graph("Gateway requests / s by status", "Every attempt that reaches the gateway, including SDK retries.",
              [target(f"sum by (mode, status) (rate(llm_gateway_requests_total{RATE}))", "{{mode}} {{status}}")], "reqps", width=8),
        graph("Gateway latency p95", "Time to answer one attempt, including injected latency.",
              [target(histogram_quantile(0.95, "llm_gateway_request_duration_seconds_bucket", "", by="mode"), "{{mode}}")],
              "s", width=8),
        graph("Injected faults / s", "Requests hit by the gateway chaos API. In a real incident this panel does not exist.",
              [target(f"sum by (fault) (rate(llm_gateway_injected_faults_total{RATE}))", "{{fault}}")], "reqps", width=8),
    ])

    return dashboard(
        "ai-assistant", "AI Assistant",
        "Golden signals, LLM calls (OpenTelemetry GenAI), tokens, cost, tools and gateway of the AI shopping assistant.",
        "ai-assistant",
        [query_variable("model", "Model", "label_values(gen_ai_client_operation_duration_seconds_count, gen_ai_request_model)",
                        "All", include_all=True)],
        [golden, slo_row("ai-assistant"), chat_row, llm, tools, gateway, Row("Saturation", saturation_panels("ai-assistant"))],
    )


def main() -> None:
    for name, build in (("retail-store", retail_store), ("ai-assistant", ai_assistant)):
        path = OUTPUT_DIR / f"{name}.json"
        path.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"Wrote {path.relative_to(OUTPUT_DIR.parent.parent.parent)}")


if __name__ == "__main__":
    main()
