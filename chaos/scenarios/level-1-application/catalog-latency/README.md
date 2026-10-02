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

- **Average latency by service**: `ui` jumps. Some pages call catalog several times, so the delay adds up.
- **Requests / s** drops: the load generator waits longer for each page.
- **5xx errors**: watch for UI timeouts.

## Diagnose

- The catalog latency is not on the dashboard (catalog is Go, the latency panel shows Java services). How do you prove catalog is the cause?
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

Follow-up: add a catalog latency panel (`gin_request_duration_seconds`) to the dashboard.

</details>
