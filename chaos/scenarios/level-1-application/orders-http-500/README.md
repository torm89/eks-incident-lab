# orders-http-500

**Level:** 1 - application &nbsp;|&nbsp; **Tool:** built-in chaos API

The orders service starts answering every API call with HTTP 500.

## Hypothesis

Browsing and the cart keep working. Placing an order fails.
Only about 4% of all store requests fail: too few for the store-wide availability SLO, but the checkout SLO pages.

## Inject

```bash
kubectl create -k chaos/scenarios/level-1-application/orders-http-500/inject
```

## Observe

- **Error ratio (5xx) by service**: only `ui`. What happens to the `orders` line in **Requests / s by service**?
- **Orders / min** drops to 0.
- Golden signal **Errors** rises a little (~4%), far from 100%.
- **Burn rate**: which SLO burns, store availability or store checkout?

## Diagnose

- Which service returns the first 5xx? Compare the panels.
- `kubectl -n retail-store logs deploy/orders`
- `kubectl -n traffic logs deploy/load-generator` - which URLs fail?

## Recover

```bash
kubectl create -k chaos/scenarios/level-1-application/orders-http-500/recover
```

## Verify

Retail Store dashboard: requests flowing, UI error ratio ~0%, orders/min > 0, all pods ready.

<details>
<summary>Solution (open after you tried)</summary>

The orders pod has the chaos flag set in memory. Its chaos filter answers before the request metrics are recorded,
so orders shows no 5xx: its traffic just disappears from the panels. Only the UI reports the errors, on `POST /checkout/payment`.

Payments are a small share of all requests, so the store-wide error ratio stays around 4%, below the 6% slow-burn threshold.
The checkout SLO (only `/checkout*` requests) sees about 25% errors and pages: a critical user journey needs its own SLO.

Two fixes:

- Call `DELETE /chaos/status` (the recover step).
- Restart the pod: `kubectl -n retail-store rollout restart deploy/orders`. A new pod starts without the flag.

</details>
