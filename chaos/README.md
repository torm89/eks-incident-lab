# Chaos

Failure injection for the Retail Store app. Each scenario is a small incident exercise:

1. **Steady state** - traffic is running, the Retail Store dashboard is green.
2. **Inject** - one command.
3. **Observe** - what changes in Grafana, and how fast.
4. **Diagnose** - find the cause with `kubectl`, logs and metrics.
5. **Recover** - fix it and verify the steady state is back.

Every scenario README has a hidden **Solution** section. Try first, then open it.

## Scenarios

| Scenario | Level | Tool | Setup |
|---|---|---|---|
| [orders-http-500](scenarios/orders-http-500/) | 1 - application | built-in chaos API | none |
| [catalog-latency](scenarios/catalog-latency/) | 1 - application | built-in chaos API | none |
| [catalog-db-pod-kill](scenarios/catalog-db-pod-kill/) | 2 - Kubernetes | Chaos Mesh | Chaos Mesh |
| [checkout-redis-network-loss](scenarios/checkout-redis-network-loss/) | 2 - Kubernetes | Chaos Mesh | Chaos Mesh |
| [node-spot-interruption](scenarios/node-spot-interruption/) | 3 - AWS | AWS FIS | `tofu apply` in the scenario |
| [node-terminate](scenarios/node-terminate/) | 3 - AWS | AWS FIS | `tofu apply` in the scenario |
| [az-network-disruption](scenarios/az-network-disruption/) | 3 - AWS | AWS FIS | `tofu apply` in the scenario |

## Layout

```
chaos/
├── chaos-mesh/          Chaos Mesh engine (level 2), Kustomize + Helm
├── base/                shared Job that calls the app's /chaos/* API (level 1)
├── modules/fis-role/    OpenTofu module: IAM role for FIS (level 3)
└── scenarios/<name>/
    ├── README.md        hypothesis, signals, runbook, solution
    ├── inject/          level 1-2: kustomization
    ├── recover/         level 1: kustomization
    └── infra/           level 3: OpenTofu root module, own state
```

## Setup per level

**Level 1** needs nothing. The app has a built-in chaos API (`/chaos/status`, `/chaos/latency`, `/chaos/health`).
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
