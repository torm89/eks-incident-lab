# Backlog

Ideas for the lab that are not built yet. Ordered by value within each section.

## New scenarios

Done, each with a fix other than a restart: [`ui-bad-deploy`](../chaos/scenarios/level-2-kubernetes/ui-bad-deploy/),
[`carts-oom`](../chaos/scenarios/level-2-kubernetes/carts-oom/), [`llm-key-invalid`](../chaos/scenarios/level-2-kubernetes/llm-key-invalid/),
[`catalog-network-policy`](../chaos/scenarios/level-2-kubernetes/catalog-network-policy/), [`traffic-spike`](../chaos/scenarios/level-2-kubernetes/traffic-spike/).

Still to build:

- `ai-cost-runaway`: a prompt or agent change makes the agent loop; cost alert, step limit, rollback.
- `prompt-regression`: a new system prompt gives worse answers; caught by a small answer-quality check (eval) before release.

## Practice and review

- **Postmortem template** (`docs/postmortem-template.md`): timeline, time to detect, time to fix, cause, lessons, actions.
- **Hardening overlay**: apply the lessons (2 replicas, PodDisruptionBudgets, persistent MySQL disk) and run the same scenario before and after.
- **Chaos markers for level 2 and 3**: Chaos Mesh experiments and FIS runs leave no dashboard marker (kube-state-metrics custom resource metrics; Grafana annotation API from `chaos.py`). Keep blind runs without markers.

## Observability

- **Customer-side SLIs**: the UI's own metrics miss requests that never reach it or wait in a queue in front of it
  (`catalog-latency`, `ai-tool-cascade`, `catalog-network-policy`, `traffic-spike`). Export the load generator's
  results (Artillery Prometheus publisher) or add blackbox probes, and base the store SLOs on them.
- **Logs in Grafana** (Loki + Alloy): diagnose without `kubectl logs`.
- **Traces** (Tempo): the app already emits OpenTelemetry; follow one request UI → checkout → orders → LLM.
- **Notifications**: Slack or Discord receiver in Alertmanager (webhook in a Secret, never in the repo). Include a dead man's switch
  for the `Watchdog` alert: in `az-network-disruption` Prometheus went blind with its AZ and nothing fired.
- **Monitoring across AZs**: 2 Prometheus replicas with anti-affinity across zones, so one AZ failure does not blind it.

## Platform and repository

- **Orders cannot publish to RabbitMQ**: the upstream `orders-rabbitmq` Secret is empty, so orders logs
  `ACCESS_REFUSED` for the `guest` user (allowed only from localhost) about twice a second. Orders still work,
  but the noise hides real errors in the logs. Set credentials in a patch, or turn messaging off.
- **CI on GitHub Actions**: `pytest`, `tofu fmt`/`validate`, `kustomize build`, `promtool` alert tests, and a check that generated dashboards and alerts are up to date.
- **Grafana screenshot or GIF** in the README, taken during an incident.
- **VPC CNI prefix delegation**: up to 110 pods per node instead of 17 on t3.medium (alternative to more nodes).
- **Daily LLM budget alert**: catches slow, long-running spend with the real API (the hourly alert misses it).
