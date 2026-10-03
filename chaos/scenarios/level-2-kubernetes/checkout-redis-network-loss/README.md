# checkout-redis-network-loss

**Level:** 2 - Kubernetes &nbsp;|&nbsp; **Tool:** Chaos Mesh `NetworkChaos`

All packets from the checkout service to its Redis are dropped for 5 minutes.

## Hypothesis

Checkout hangs and fails. Browsing and the cart keep working. Everything recovers by itself after 5 minutes.

## Inject

```bash
kubectl apply -k chaos/scenarios/level-2-kubernetes/checkout-redis-network-loss/inject
```

## Observe

- **Errors** and **UI latency: successful vs failed**.
- **Orders / min** drops to 0.
- **Pods ready**: does checkout fail its probes?

## Diagnose

- `kubectl -n retail-store logs deploy/checkout` - connection errors? To what?
- `kubectl -n chaos-mesh get networkchaos` - in a real incident you would not have this hint.
- `kubectl -n retail-store get pods -l app.kubernetes.io/component=redis` - is Redis itself healthy?

## Recover

```bash
kubectl delete -k chaos/scenarios/level-2-kubernetes/checkout-redis-network-loss/inject
```

## Verify

Retail Store dashboard: requests flowing, UI error ratio ~0%, orders/min > 0, all pods ready.

<details>
<summary>Solution (open after you tried)</summary>

Pods and services look healthy, the network between them is broken. Logs show Redis timeouts.

The experiment ends by itself after 5 minutes; deleting it ends it at once.

Lesson: a dependency failure shows up as slowness first (timeouts), errors later.

</details>
