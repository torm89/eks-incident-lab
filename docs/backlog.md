# Backlog

Ideas for the lab that are not built yet. Ordered by value within each section.

## New scenarios: where a restart does not help

Most current scenarios are fixed by restarting a deployment (the failure lives in process memory).
That teaches a bad reflex: in real incidents a restart is only one tool, and often a dead end.
Each scenario below needs a different fix.

| Scenario | Level | Failure | Fix it teaches | Why a restart fails |
|---|---|---|---|---|
| `ui-bad-deploy` | 2 | A new UI version with a bug (wrong image tag or broken config) | `kubectl rollout undo` | the new pods run the same broken version |
| `llm-key-invalid` | 1 | The `anthropic-api-key` Secret holds an invalid key (real-API mode) or the gateway rejects it (mock: inject 401) | fix the Secret, then roll the gateway | a restart reloads the same bad key |
| `carts-oom` | 2 | The carts memory limit is lowered below what it needs | raise the limit | the pod is OOM-killed again (CrashLoopBackOff) |
| `catalog-network-policy` | 2 | A NetworkPolicy blocks traffic to catalog | find and remove the policy | pods are healthy, the network path is not |
| `traffic-spike` | 1 | 10x more synthetic traffic | scale out (more replicas), rate limiting | more of the same pods are needed, not new ones |

Start with `ui-bad-deploy`, `llm-key-invalid` and `carts-oom`: the most common in real incidents.

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
