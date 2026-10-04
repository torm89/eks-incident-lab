# node-terminate

**Level:** 3 - AWS &nbsp;|&nbsp; **Tool:** AWS FIS `aws:eks:terminate-nodegroup-instances`

Half of the node group (FIS rounds the share of 3 nodes) is terminated with no warning.

## Hypothesis

Like a spot interruption, but sudden: 50% of the node group (1 of 3 nodes) is terminated with no warning, so nothing
drains it. Its pods die and start again on the other nodes; the replacement node is `Ready` within about 3 minutes.
As with a spot interruption, data stores that lived on that node start again empty, and the store stays broken
until the services that use them are restarted.

## Inject

```bash
uv run scripts/lab.py state-backend   # only if you keep state in S3 (backend.hcl)
cd chaos/scenarios/level-3-aws/node-terminate/infra && tofu init && tofu apply
```

```bash
tofu output -raw start_experiment   # prints the start command: run it
```

## Observe

- **Pods ready** drops sharply. **Errors** goes up: does it come back down when all pods are ready again?
- **Node CPU and memory** and **Pods per node, % of max** on the surviving nodes: is there room for everything?
- `kubectl get pods -A --field-selector=status.phase=Pending`

## Diagnose

- Pods `Pending`? `kubectl describe pod <pod>` - not enough CPU/memory, or too many pods per node?
- How long until the new node is `Ready`?
- Which data stores were on the lost node (`kubectl -n retail-store get pods -o wide`, look at the ages)?
  Logs of the services that use them: `kubectl -n retail-store logs deploy/carts --tail=20` (and catalog, orders).

## Recover

The node group replaces the node by itself. Then restart the services whose data store came back empty,
for example carts after `carts-dynamodb`:

```bash
kubectl -n retail-store rollout restart deploy/carts
```

## Verify

Retail Store dashboard: requests flowing, UI error ratio ~0%, orders/min > 0, all pods ready. Three nodes `Ready`.

<details>
<summary>Solution (open after you tried)</summary>

With 3 nodes, the 2 survivors have room for the pods of the lost one, so few or no pods stay `Pending`.
(Each `t3.medium` runs at most 17 pods: with fewer nodes, check **Pods per node, % of max**.)

The long outage comes from the data, as in `node-spot-interruption`: a terminated node takes its `emptyDir` volumes
with it. When `carts-dynamodb` was on it, carts loses its table (`ResourceNotFoundException`) and every page fails,
because every page shows the cart. Carts creates its table only at startup: restart it.

Lessons: capacity headroom, resource requests, priority classes for the most important pods, and state on
persistent volumes, not on the node.

Cleanup when done practicing: `tofu destroy` in `infra/`.

</details>
