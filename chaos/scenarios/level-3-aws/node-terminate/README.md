# node-terminate

**Level:** 3 - AWS &nbsp;|&nbsp; **Tool:** AWS FIS `aws:eks:terminate-nodegroup-instances`

Half of the node group (FIS rounds the share of 3 nodes) is terminated with no warning.

## Hypothesis

Like a spot interruption, but sudden. The cluster runs on the remaining nodes until the replacements are ready.

## Inject

```bash
uv run scripts/lab.py state-backend   # only if you keep state in S3 (backend.hcl)
cd chaos/scenarios/level-3-aws/node-terminate/infra && tofu init && tofu apply
```

```bash
tofu output -raw start_experiment   # prints the start command: run it
```

## Observe

- **Pods ready** drops sharply.
- **Node CPU and memory** and **Pods per node, % of max** on the surviving node: is there room for everything?
- `kubectl get pods -A --field-selector=status.phase=Pending`

## Diagnose

- Pods `Pending`? `kubectl describe pod <pod>` - not enough CPU/memory, or too many pods per node?
- How long until the new node is `Ready`?

## Recover

```bash
# Nothing to do: the node group replaces the node. Watch it:
kubectl get nodes -w
```

## Verify

Retail Store dashboard: requests flowing, UI error ratio ~0%, orders/min > 0, all pods ready. Three nodes `Ready`.

<details>
<summary>Solution (open after you tried)</summary>

Each `t3.medium` runs at most 17 pods. If the remaining nodes have no free pod slots or memory, some pods stay `Pending` until new nodes join (a few minutes). Check **Pods per node, % of max**.

Lessons: capacity headroom, resource requests, priority classes for the most important pods.

Cleanup when done practicing: `tofu destroy` in `infra/`.

</details>
