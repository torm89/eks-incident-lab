# traffic-spike

**Level:** 2 - Kubernetes &nbsp;|&nbsp; **Tool:** `kubectl apply` (the load generator)

A marketing campaign works too well: 30 times more customers arrive. Nothing is broken, there is just not enough capacity.

## Hypothesis

Customers wait seconds for pages and many requests time out. The UI's own metrics look almost fine: requests wait in a
queue in front of the UI, and the UI starts its clock only when it picks a request up. The UI pod keeps dropping out of
its Service (readiness probe timeouts), and the throughput goes **down**, not up. No SLO alert fires.
Restarting does not help: the same number of pods gets the same load. More pods are needed.

Treat the `traffic` namespace as your customers: in the fix, do not touch it.

## Inject

```bash
kubectl apply -k chaos/scenarios/level-2-kubernetes/traffic-spike/inject
```

## Observe

- **Traffic** and **Requests / s by service**: how much more than usual? Does it keep up with 30x?
- **Latency p95** and **Errors**: do they show what customers feel? Compare with the load generator:
  `kubectl -n traffic logs deploy/load-generator --tail=40` (`http.response_time`, `errors.ERR_SOCKET_TIMEOUT`).
- **Pods ready**: does the UI stay ready?
- **CPU by pod** and `kubectl top nodes`: which pods and nodes work hardest?

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
Then check the nodes: `kubectl top nodes`. If one runs near 100%, more replicas only move the queue: the cluster needs
more nodes (`node_count` in `infra/variables.tf`, then `tofu apply`, or a cluster autoscaler).

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

The load generator now starts 30 new customer sessions per second instead of 1. Every service runs 1 replica.
The UI cannot accept requests as fast as they come: they queue in front of it, its readiness probe times out, and the
pod flaps in and out of its Service (`PodReadinessFlapping`). One node runs hot (the catalog MySQL and the load generator).

The server-side metrics miss most of it: the UI measures only the time after it picked a request up, so its p95 stays
low while customers wait 5-10 s, and timeouts in the queue are not errors to the UI. The SLOs stay green.
At 10x the store still copes; the first sign there is the same readiness flapping.

The fix is capacity: more replicas, so the load is spread. In this lab 3 UI replicas raise the throughput by about
half but do not end the timeouts: the 3 small nodes run out of CPU (the load generator runs on them too). Then the
cluster needs more nodes (`node_count` in `infra/`, or a cluster autoscaler). If new pods stay `Pending`, the nodes are full.

Lesson: an overload looks like a failure (slow, errors), but nothing is broken. A restart only adds a cold start.
Check the saturation signals (CPU, queueing, readiness flapping) before you look for a bug,
and measure what customers feel from the outside too: server-side latency cannot see the queue in front of the server.
A real fix is automatic: a HorizontalPodAutoscaler on CPU (`kubectl -n retail-store autoscale deploy/ui --cpu-percent=70 --min=1 --max=4`
works here: metrics-server is installed), rate limiting at the edge, and capacity headroom.

</details>
