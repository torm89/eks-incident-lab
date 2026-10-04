# az-network-disruption

**Level:** 3 - AWS &nbsp;|&nbsp; **Tool:** AWS FIS `aws:network:disrupt-connectivity`

The worker node subnets in `eu-west-1a` lose all network traffic for 5 minutes. Works in both `node_subnet_type` modes.

## Hypothesis

The nodes in that AZ (often 2 of the 3) become `NotReady` within a minute. Their pods are unreachable, but Kubernetes
waits about 5 minutes before moving them, so the outage lasts about as long as the failure, and ends by itself.
If Prometheus runs in that AZ, the monitoring goes blind at the same moment: the store is down and no alert fires.

## Inject

```bash
uv run scripts/lab.py state-backend   # only if you keep state in S3 (backend.hcl)
cd chaos/scenarios/level-3-aws/az-network-disruption/infra && tofu init && tofu apply
```

```bash
tofu output -raw start_experiment   # prints the start command: run it
```

## Observe

- `kubectl get nodes -w` - when do the nodes become `NotReady`?
- Where does Prometheus run? `kubectl -n monitoring get pods -o wide`. Which AZ is that node in?
- The customers' view: `kubectl -n traffic logs deploy/load-generator --tail=40` (if it runs outside that AZ).
- **Errors** and **Traffic** on the dashboard: gaps, or real values? Did any alert fire?

## Diagnose

- Pods on the `NotReady` node still show `Running` for a while. Why?
- `kubectl describe node <node>` - conditions and taints.

## Recover

```bash
# Ends by itself after 5 minutes. Stop it earlier:
aws fis stop-experiment --region eu-west-1 --id <experiment-id>
```

## Verify

Retail Store dashboard: requests flowing, UI error ratio ~0%, orders/min > 0, all pods ready. Three nodes `Ready`.

<details>
<summary>Solution (open after you tried)</summary>

The nodes get the `node.kubernetes.io/unreachable` taint. Pods tolerate it for 300 s by default, so they are not moved
before the disruption ends. The UI in the healthy AZ cannot reach catalog, carts and orders: customers get timeouts and
500s for the whole disruption, then everything recovers at once. Data stores in the healthy AZ keep their data.

When Prometheus and kube-state-metrics run in the cut-off AZ, they scrape only the targets next to them: the store's
metrics are **missing**, not bad, so no SLO alert and no `StoreTrafficLost` fires. The dashboards show a gap, at best.
The `Watchdog` alert exists for this: an external receiver that pages when Watchdog stops arriving
(a dead man's switch). The lab's Alertmanager has no receivers, so nobody notices.

Lessons: spread replicas across AZs (topology spread constraints), shorter tolerations for critical pods,
and monitoring that does not share the failure domain of what it watches (2 Prometheus replicas in different AZs,
or an external dead man's switch).

Cleanup when done practicing: `tofu destroy` in `infra/`.

</details>
