# Backlog

Ideas for the lab that are not built yet. Ordered by value within each section.

## New scenarios: where a restart does not help

Most current scenarios are fixed by restarting a deployment (the failure lives in process memory).
That teaches a bad reflex: in real incidents a restart is only one tool, and often a dead end.
Each scenario below needs a different fix.

| Scenario | Level | Failure | Fix it teaches | Why a restart fails |
|---|---|---|---|---|
| `traffic-spike` | 2 | 10x more synthetic traffic (more replicas of the traffic Deployment) | scale out (more replicas), rate limiting | more of the same pods are needed, not new ones |

Done: [`ui-bad-deploy`](../chaos/scenarios/level-2-kubernetes/ui-bad-deploy/), [`carts-oom`](../chaos/scenarios/level-2-kubernetes/carts-oom/), [`llm-key-invalid`](../chaos/scenarios/level-2-kubernetes/llm-key-invalid/), [`catalog-network-policy`](../chaos/scenarios/level-2-kubernetes/catalog-network-policy/).

Prerequisites and pitfalls:

- `traffic-spike`: the traffic generator is a Deployment, so inject is a Kustomize patch (level 2), not the app's chaos API. Watch node capacity (17 pods per t3.medium node): scaled-out pods may stay `Pending`, which is a lesson of its own (cluster autoscaling, or prefix delegation below).

Also worth a scenario later:

- `ai-cost-runaway`: a prompt or agent change makes the agent loop; cost alert, step limit, rollback.
- `prompt-regression`: a new system prompt gives worse answers; caught by a small answer-quality check (eval) before release.

## Practice and review

- **Postmortem template** (`docs/postmortem-template.md`): timeline, time to detect, time to fix, cause, lessons, actions.
- **Hardening overlay**: apply the lessons (2 replicas, PodDisruptionBudgets, persistent MySQL disk) and run the same scenario before and after.
- **Chaos markers for level 2 and 3**: Chaos Mesh experiments and FIS runs leave no dashboard marker (kube-state-metrics custom resource metrics; Grafana annotation API from `chaos.py`). Keep blind runs without markers.

## Observability

- **Logs in Grafana** (Loki + Alloy): diagnose without `kubectl logs`.
- **Traces** (Tempo): the app already emits OpenTelemetry; follow one request UI → checkout → orders → LLM.
- **Notifications**: Slack or Discord receiver in Alertmanager (webhook in a Secret, never in the repo).

## Platform and repository

- **CI on GitHub Actions**: `pytest`, `tofu fmt`/`validate`, `kustomize build`, `promtool` alert tests, and a check that generated dashboards and alerts are up to date.
- **Grafana screenshot or GIF** in the README, taken during an incident.
- **VPC CNI prefix delegation**: up to 110 pods per node instead of 17 on t3.medium (alternative to more nodes).
- **Daily LLM budget alert**: catches slow, long-running spend with the real API (the hourly alert misses it).
