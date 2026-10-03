# Chaos

Failure injection for the Retail Store app. Each scenario is a small incident exercise:

1. **Steady state** - traffic is running, the Retail Store dashboard is green.
2. **Inject** - one command.
3. **Observe** - what changes in Grafana, and how fast.
4. **Diagnose** - find the cause with `kubectl`, logs and metrics.
5. **Recover** - fix it and verify the steady state is back.

Every scenario README has a hidden **Solution** section. Try first, then open it.

Practice **blind**: the dashboards show an orange **Pages** marker (critical alerts) and blue **Rollouts** markers, but no hint
when the failure started: the **Chaos injected** / **Chaos recovered** markers are off by default, and `chaos.py inject --random`
leaves no data for them at all. Measure your **time to detect** with `uv run scripts/chaos.py reveal` (injection time)
and the first orange marker.
Expected alerts per scenario:

| Scenario | Expected alerts |
|---|---|
| orders-http-500 | `StoreAvailabilityBudgetBurnSlow` (or `...Fast`, depending on how many requests hit orders) |
| catalog-latency | `StoreLatencyBudgetBurn*` |
| llm-rate-limit | `AssistantAvailabilityBudgetBurnFast`, `LlmRetryAmplification` |
| llm-slow | `AssistantLatencyBudgetBurn*` |
| ai-tool-cascade | `AssistantToolQualityBudgetBurnFast`, `StoreLatencyBudgetBurn*` |
| catalog-db-pod-kill | `DataStoreNotReady`, `StoreAvailabilityBudgetBurn*` |
| checkout-redis-network-loss | `StoreLatencyBudgetBurn*` and/or `StoreAvailabilityBudgetBurn*` |
| node-spot-interruption, node-terminate, az-network-disruption | built-in `KubeNodeNotReady` / `KubePodNotReady`, plus SLO alerts for the affected services |

The SLO alerts are verified by unit tests; the per-scenario mapping is the hypothesis to check during practice.


## Quick start: scripts/chaos.py

```bash
uv run scripts/chaos.py list                         # all scenarios
uv run scripts/chaos.py inject orders-http-500       # a chosen scenario
uv run scripts/chaos.py inject --random              # blind: random level 1-2 scenario, name hidden
uv run scripts/chaos.py inject --random --level 3 --profile <aws-profile>   # blind AWS FIS (costs money)
uv run scripts/chaos.py reveal                       # which scenario, and how long ago (time to detect)
uv run scripts/chaos.py recover                      # undo it (the "cheat" button)
```

Blind mode prints no commands and deletes its chaos Jobs right after they run, so nothing gives the scenario away
except the symptoms. Chaos Mesh is installed automatically the first time it is needed.
The commands in each scenario README still work if you prefer doing it by hand.

## Scenarios

| Scenario | Level | Tool | Setup |
|---|---|---|---|
| [orders-http-500](scenarios/level-1-application/orders-http-500/) | 1 - application | built-in chaos API | none |
| [catalog-latency](scenarios/level-1-application/catalog-latency/) | 1 - application | built-in chaos API | none |
| [llm-rate-limit](scenarios/level-1-application/llm-rate-limit/) | 1 - application (AI) | llm-gateway chaos API | AI assistant |
| [llm-slow](scenarios/level-1-application/llm-slow/) | 1 - application (AI) | llm-gateway chaos API | AI assistant |
| [ai-tool-cascade](scenarios/level-1-application/ai-tool-cascade/) | 1 - application (AI) | built-in chaos API | AI assistant |
| [catalog-db-pod-kill](scenarios/level-2-kubernetes/catalog-db-pod-kill/) | 2 - Kubernetes | Chaos Mesh | Chaos Mesh |
| [checkout-redis-network-loss](scenarios/level-2-kubernetes/checkout-redis-network-loss/) | 2 - Kubernetes | Chaos Mesh | Chaos Mesh |
| [node-spot-interruption](scenarios/level-3-aws/node-spot-interruption/) | 3 - AWS | AWS FIS | `tofu apply` in the scenario |
| [node-terminate](scenarios/level-3-aws/node-terminate/) | 3 - AWS | AWS FIS | `tofu apply` in the scenario |
| [az-network-disruption](scenarios/level-3-aws/az-network-disruption/) | 3 - AWS | AWS FIS | `tofu apply` in the scenario |

## Layout

```
chaos/
├── chaos-mesh/                 Chaos Mesh engine (level 2), Kustomize + Helm
├── base/                       shared Job that calls the app's /chaos/* API (level 1)
├── modules/fis-role/           OpenTofu module: IAM role for FIS (level 3)
└── scenarios/
    ├── level-1-application/    built-in chaos API
    │   └── <name>/             README.md, inject/, recover/ (Kustomize)
    ├── level-2-kubernetes/     Chaos Mesh
    │   └── <name>/             README.md, inject/ (Kustomize)
    └── level-3-aws/            AWS FIS
        └── <name>/             README.md, infra/ (OpenTofu root, own state)
```

## Setup per level

**Level 1** needs nothing. The app has a built-in chaos API (`/chaos/status`, `/chaos/latency`, `/chaos/health`).
Our `llm-gateway` has the same `/chaos/status` and `/chaos/latency` API, so the AI scenarios reuse the same Job. They need the AI assistant (`apps/ai-assistant/README.md`).
Scenarios use `kubectl create -k`. The Job deletes itself 60 s after it finishes; wait that long before running the same step again.

**Level 2** needs Chaos Mesh, once per cluster (CRDs first):

```bash
kubectl apply --server-side -k chaos/chaos-mesh/crds
kubectl kustomize --enable-helm chaos/chaos-mesh | kubectl apply --server-side -f -
kubectl -n chaos-mesh port-forward svc/chaos-dashboard 2333:2333   # optional UI: http://localhost:2333
```

**Level 3** uses AWS FIS. Each scenario has its own OpenTofu root in `infra/` with its own state and an IAM role limited to that scenario.
Templates find targets by tags, so they can be created before the cluster exists.
Templates are free; a running experiment costs about $0.10 per action-minute.
Run `tofu destroy` in the scenario's `infra/` when you are done practicing.
