# catalog-latency

**Level:** 1 - application &nbsp;|&nbsp; **Tool:** built-in chaos API

Every catalog API call gets 2 seconds of extra delay.

## Hypothesis

The whole store gets slow, but there are no errors.

## Inject

```bash
kubectl create -k chaos/scenarios/level-1-application/catalog-latency/inject
```

## Observe

- Golden signal **Latency p95** jumps. Some pages call catalog several times, so the delay adds up.
- **Traffic** drops: the load generator waits longer for each page.
- **Errors**: watch for UI timeouts.

## Diagnose

- **Latency p95 by service**: which service got slow first, `ui` or `catalog`? The slowest dependency is usually the cause.
- `kubectl -n retail-store exec deploy/ui -- curl -s -o /dev/null -w '%{time_total}\n' http://catalog/catalog/products`

## Recover

```bash
kubectl create -k chaos/scenarios/level-1-application/catalog-latency/recover
```

## Verify

Retail Store dashboard: requests flowing, UI error ratio ~0%, orders/min > 0, all pods ready.

<details>
<summary>Solution (open after you tried)</summary>

Slow is harder to spot than broken: nothing is red. The UI shows the symptom, catalog is the cause.

Fix: `DELETE /chaos/latency` or `kubectl -n retail-store rollout restart deploy/catalog`.

Lesson: look at latency per service, not only at the entry point. The UI shows the symptom; **Latency p95 by service** shows the cause.

</details>
