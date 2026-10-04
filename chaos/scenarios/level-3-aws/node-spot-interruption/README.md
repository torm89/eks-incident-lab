# node-spot-interruption

**Level:** 3 - AWS &nbsp;|&nbsp; **Tool:** AWS FIS `aws:ec2:send-spot-instance-interruptions`

One spot worker node gets the 2-minute interruption notice, then AWS stops it.

## Hypothesis

The node group starts a replacement node at once, drains the doomed node and moves its pods. Single-replica services
are down for a minute or two. Data stores that lived on that node (`emptyDir`) start again **empty**: the store stays
broken after every pod is `Running` again, until the services that seed data at startup are restarted.

## Inject

```bash
uv run scripts/lab.py state-backend   # only if you keep state in S3 (backend.hcl)
cd chaos/scenarios/level-3-aws/node-spot-interruption/infra && tofu init && tofu apply
```

```bash
tofu output -raw start_experiment   # prints the start command: run it
```

## Observe

- `kubectl get nodes -w` - when does a new node join? When is the old one `SchedulingDisabled`, when is it gone?
- **Pods ready** drops, then recovers. Does **Errors** recover too?
- **Orders / min**: is it back to normal?

## Diagnose

- Was the node drained during the 2-minute notice, or did the pods just die? `kubectl get events -A --sort-by=.lastTimestamp`
- Which pods were on the lost node? Which had only 1 replica? Which of them keep data (`*-mysql-*`, `*-postgresql-*`, `*-redis-*`)?
- Logs of the services behind the failing pages: `kubectl -n retail-store logs deploy/catalog --tail=20`, same for `orders`.

## Recover

The node group replaces the node by itself. Then restart the services whose data store came back empty
(here: catalog and orders, if their databases were on the lost node):

```bash
kubectl -n retail-store rollout restart deploy/catalog deploy/orders
```

## Verify

Retail Store dashboard: requests flowing, UI error ratio ~0%, orders/min > 0, all pods ready. Three nodes `Ready`.

<details>
<summary>Solution (open after you tried)</summary>

EKS managed node groups handle the spot interruption notice: they launch a replacement, cordon and drain the old node.
The pods move in time, so the outage of the moved services is short.

The long outage comes from the data: MySQL and PostgreSQL keep their data in `emptyDir`, which dies with the node.
They start empty, catalog answers 404 (`Table 'catalog.products' doesn't exist`) and orders fails
(`relation "orders" does not exist`). Both create their schema only at startup, so they need a restart.
Nothing on the Kubernetes side looks wrong: the SLO alerts and the logs are the way in.

Lessons: a node is cattle, its local disk too. Keep state on persistent volumes (EBS + PVC) or in managed services,
run 2+ replicas of important services, add PodDisruptionBudgets.

Cleanup when done practicing: `tofu destroy` in `infra/`.

</details>
