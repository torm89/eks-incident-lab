# traffic-spike

**Level:** 2 - Kubernetes &nbsp;|&nbsp; **Tool:** `kubectl apply` (the load generator)

A marketing campaign works too well: 10 times more customers arrive. Nothing is broken, there is just not enough capacity.

## Hypothesis

Latency rises first, then some requests fail. CPU of the busiest services climbs. Every pod is healthy.
Restarting does not help: the same number of pods gets the same load. More pods are needed.

Treat the `traffic` namespace as your customers: in the fix, do not touch it.

## Inject

```bash
kubectl apply -k chaos/scenarios/level-2-kubernetes/traffic-spike/inject
```

## Observe

- **Traffic** and **Requests / s by service**: how much more than usual?
- **Latency p95** and **Latency by service**: which service gets slow first?
- **CPU by pod**: which pods work hardest? Compare with their CPU request.
- **Errors**: does the error ratio rise too, or only latency?

## Diagnose

- `kubectl -n retail-store top pods` and `kubectl top nodes` - where is the CPU going? Is a node busy?
- `kubectl describe nodes` → **Allocated resources** - is there room (by requests) for more pods?
- `kubectl -n retail-store get deploy` - how many replicas does each service have?
- `kubectl -n retail-store describe deploy/ui` - CPU request and limit?
- Is anything broken (restarts, errors in logs), or just busy?

## Recover

Scale out the bottleneck (usually the UI first, then the service behind it):

```bash
kubectl -n retail-store scale deploy/ui --replicas=3
kubectl -n retail-store scale deploy/catalog --replicas=2
```

Check that the new pods start: `kubectl -n retail-store get pods -o wide`. Any `Pending`?

When the campaign is over (what `scripts/chaos.py recover` does), back to the normal traffic and size:

```bash
kubectl apply -k chaos/scenarios/level-2-kubernetes/traffic-spike/recover
kubectl apply -k apps/retail-store
```

## Verify

Retail Store dashboard: latency p95 under the SLO (1 s) while the traffic stays 10x higher, error ratio ~0%,
CPU spread over more pods.

<details>
<summary>Solution (open after you tried)</summary>

The load generator now starts 10 new customer sessions per second instead of 1. Every service runs 1 replica, so
the busiest ones (the UI, which renders every page, and the catalog behind it) run out of CPU: requests queue and latency grows.

The fix is capacity: more replicas, so the load is spread. If new pods stay `Pending`, the nodes are full:
then the cluster needs more nodes (`node_count` in `infra/`, or a cluster autoscaler) or more pods per node.

Lesson: an overload looks like a failure (slow, errors), but nothing is broken. A restart only adds a cold start.
Check the saturation signals (CPU, queueing) before you look for a bug.
A real fix is automatic: a HorizontalPodAutoscaler on CPU (`kubectl -n retail-store autoscale deploy/ui --cpu-percent=70 --min=1 --max=4`
works here: metrics-server is installed), rate limiting at the edge, and capacity headroom.

</details>
