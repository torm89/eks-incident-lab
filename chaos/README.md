# Chaos

Failure injection for the Retail Store app. Each experiment is a small exercise:

1. **Steady state** - traffic is running, the Retail Store dashboard is green.
2. **Inject** - start the experiment.
3. **Detect** - watch what changes in Grafana and how fast.
4. **Diagnose** - find the cause with `kubectl`, logs and metrics.
5. **Recover** - fix it and confirm the steady state is back.

## AWS level - AWS Fault Injection Service (`infra/`)

OpenTofu root module with its own state (`chaos/terraform.tfstate`).
Experiment templates find their targets by tags, so they can be created before the cluster exists.
Templates are free; a running experiment costs about $0.10 per action-minute.

```bash
cd chaos/infra
tofu init
tofu apply
tofu output                     # start commands for each experiment
```

| Experiment | What happens | Hypothesis |
|---|---|---|
| `node-spot-interruption` | One spot node gets a 2-minute interruption notice, then stops. | Pods on that node go `Pending`, then start on the other node. Single-replica services are down until then. The node group launches a replacement. |
| `node-terminate` | 50% of the node group (one node) is terminated at once. | Like the spot interruption, but with no warning. Recovery takes longer. |
| `az-network-disruption` | Private subnets in `eu-west-1a` lose all network traffic for 5 minutes. | The node in that AZ becomes `NotReady`. Its pods are unreachable, but Kubernetes waits 5 minutes before moving them. |

Watch an experiment:

```bash
aws fis get-experiment --profile <aws-profile> --region eu-west-1 --id <experiment-id> --query experiment.state
kubectl get nodes -w
```
