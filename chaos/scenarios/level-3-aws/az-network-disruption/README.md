# az-network-disruption

**Level:** 3 - AWS &nbsp;|&nbsp; **Tool:** AWS FIS `aws:network:disrupt-connectivity`

The worker node subnets in `eu-west-1a` lose all network traffic for 5 minutes. Works in both `node_subnet_type` modes.

## Hypothesis

The node in that AZ becomes `NotReady`. Its pods are unreachable, but Kubernetes waits about 5 minutes before moving them, so the outage lasts about as long as the failure.

## Inject

```bash
cd chaos/scenarios/level-3-aws/az-network-disruption/infra && tofu init && tofu apply
```

```bash
tofu output -raw start_experiment   # prints the start command: run it
```

## Observe

- `kubectl get nodes -w` - when does the node become `NotReady`?
- **5xx errors / s** and **Ready pods**.
- Prometheus itself may run in that AZ: are there gaps in the graphs?

## Diagnose

- Pods on the `NotReady` node still show `Running` for a while. Why?
- `kubectl describe node <node>` - conditions and taints.

## Recover

```bash
# Ends by itself after 5 minutes. Stop it earlier:
aws fis stop-experiment --profile <aws-profile> --region eu-west-1 --id <experiment-id>
```

## Verify

Retail Store dashboard: requests flowing, UI error ratio ~0%, orders/min > 0, all pods ready. Two nodes `Ready`.

<details>
<summary>Solution (open after you tried)</summary>

The node gets the `node.kubernetes.io/unreachable` taint. Pods tolerate it for 300 s by default, so they are not moved before the disruption ends.

Lessons: spread replicas across AZs (topology spread constraints), shorter tolerations for critical pods.

Cleanup when done practicing: `tofu destroy` in `infra/`.

</details>
