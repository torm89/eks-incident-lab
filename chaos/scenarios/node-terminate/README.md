# node-terminate

**Level:** 3 - AWS &nbsp;|&nbsp; **Tool:** AWS FIS `aws:eks:terminate-nodegroup-instances`

Half of the node group (one node) is terminated with no warning.

## Hypothesis

Like a spot interruption, but sudden. The cluster runs on one node until the replacement is ready.

## Inject

```bash
cd chaos/scenarios/node-terminate/infra && tofu init && tofu apply
```

```bash
tofu output -raw start_experiment   # prints the start command: run it
```

## Observe

- **Ready pods** drops sharply.
- **CPU / Memory by pod** on the surviving node: is there room for everything?
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

Retail Store dashboard: requests flowing, UI error ratio ~0%, orders/min > 0, all pods ready. Two nodes `Ready`.

<details>
<summary>Solution (open after you tried)</summary>

One `t3.medium` cannot hold the whole cluster: some pods stay `Pending` until the new node joins (a few minutes).

Lessons: capacity headroom, resource requests, priority classes for the most important pods.

Cleanup when done practicing: `tofu destroy` in `infra/`.

</details>
