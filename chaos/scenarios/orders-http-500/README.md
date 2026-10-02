# orders-http-500

**Level:** 1 - application &nbsp;|&nbsp; **Tool:** built-in chaos API

The orders service starts answering every API call with HTTP 500.

## Hypothesis

Browsing and the cart keep working. Placing an order fails.

## Inject

```bash
kubectl create -k chaos/scenarios/orders-http-500/inject
```

## Observe

- **5xx errors / s by service**: `orders`, then `ui`.
- **Orders / min** drops to 0.
- **UI error ratio** rises, but not to 100%.

## Diagnose

- Which service returns the first 5xx? Compare the panels.
- `kubectl -n retail-store logs deploy/orders`
- `kubectl -n traffic logs deploy/load-generator` - which URLs fail?

## Recover

```bash
kubectl create -k chaos/scenarios/orders-http-500/recover
```

## Verify

Retail Store dashboard: requests flowing, UI error ratio ~0%, orders/min > 0, all pods ready.

<details>
<summary>Solution (open after you tried)</summary>

The orders pod has the chaos flag set in memory. Two fixes:

- Call `DELETE /chaos/status` (the recover step).
- Restart the pod: `kubectl -n retail-store rollout restart deploy/orders`. A new pod starts without the flag.

</details>
