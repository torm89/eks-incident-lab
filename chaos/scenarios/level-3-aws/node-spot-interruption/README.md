# node-spot-interruption

**Level:** 3 - AWS &nbsp;|&nbsp; **Tool:** AWS FIS `aws:ec2:send-spot-instance-interruptions`

One spot worker node gets the 2-minute interruption notice, then AWS stops it.

## Hypothesis

Pods on that node go `Pending` and start on the other node. Single-replica services are down for a few minutes. The node group launches a replacement node.

## Inject

```bash
cd chaos/scenarios/level-3-aws/node-spot-interruption/infra && tofu init && tofu apply
```

```bash
tofu output -raw start_experiment   # prints the start command: run it
```

## Observe

- **Pods ready** drops, then recovers.
- **Error ratio (5xx) by service**: which services break, and for how long?
- `kubectl get nodes -w`

## Diagnose

- Was the node drained during the 2-minute notice, or did the pods just die? `kubectl get events -A --sort-by=.lastTimestamp`
- Which pods were on the lost node? Which had only 1 replica?

## Recover

```bash
# Nothing to do: the node group replaces the node. Watch it:
kubectl get nodes -w
```

## Verify

Retail Store dashboard: requests flowing, UI error ratio ~0%, orders/min > 0, all pods ready. Two nodes `Ready`.

<details>
<summary>Solution (open after you tried)</summary>

Managed node groups replace the instance, but nothing drains the node on the interruption notice itself. Pods are killed hard and rescheduled.

Lessons: run 2+ replicas of important services, add PodDisruptionBudgets, consider the AWS Node Termination Handler.

Cleanup when done practicing: `tofu destroy` in `infra/`.

</details>
