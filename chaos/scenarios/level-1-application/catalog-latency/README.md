# catalog-latency

**Level:** 1 - application &nbsp;|&nbsp; **Tool:** built-in chaos API

Every catalog API call gets 2 seconds of extra delay.

## Hypothesis

The whole store gets slow. The dashboards show no 5xx errors, yet customers get timeouts:
the UI stops coping, fails its readiness probe and drops in and out of its Service.

## Inject

```bash
kubectl create -k chaos/scenarios/level-1-application/catalog-latency/inject
```

## Observe

- Golden signal **Latency p95** jumps. Some pages call catalog several times, so the delay adds up.
- **Traffic** collapses (about 18 to 1 request/s): requests that never reach the UI are not counted at all.
- **Errors** stays at 0%. Compare with the load generator: `kubectl -n traffic logs deploy/load-generator --tail=20`.
- **Pods ready**: the UI pod goes not ready, then ready again.
- How long until the first page? The latency alert needs most of its 5-minute window to be slow.

## Diagnose

- **Latency by service**: which service got slow first, `ui` or `catalog`? The slowest dependency is usually the cause.
- `kubectl -n retail-store exec deploy/ui -- curl -s -o /dev/null -w '%{time_total}\n' http://catalog/catalog/products`

## Recover

```bash
kubectl create -k chaos/scenarios/level-1-application/catalog-latency/recover
```

## Verify

Retail Store dashboard: requests flowing, UI error ratio ~0%, orders/min > 0, all pods ready.

<details>
<summary>Solution (open after you tried)</summary>

Slow is harder to spot than broken. The UI shows the symptom, catalog is the cause.

The UI is a reactive (Spring WebFlux) app with a few request threads. Its catalog client waits on those threads, so
2 s per catalog call blocks them, and even the readiness probe (1 s timeout) cannot get an answer. The pod leaves the
Service; the load generator gets socket timeouts. The UI's own metrics see only the few requests that got through:
no 5xx, and a request rate close to zero. That also delays the SLO alert: fast requests from before the injection
dilute the 5-minute window, and it pages after about 5 minutes instead of 2. `StoreTrafficLost` catches the missing requests.

Fix: `DELETE /chaos/latency` or `kubectl -n retail-store rollout restart deploy/catalog`.

Lesson: look at latency per service, not only at the entry point. The UI shows the symptom; **Latency by service** shows the cause.
A drop in traffic is a symptom too: server-side metrics cannot count requests that never arrive.
A real fix is a timeout (and a fallback) on the catalog call, so one slow dependency cannot take the whole UI down.

</details>
