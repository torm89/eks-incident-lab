# ui-bad-deploy

**Level:** 2 - Kubernetes &nbsp;|&nbsp; **Tool:** `kubectl apply` (a bad release)

A new UI release goes out with a broken configuration. Nothing crashes: the pod starts and is `Ready`.

## Hypothesis

Product pages fail right after the rollout. Restarting the UI does not help: the new pods run the same broken release.

## Inject

```bash
kubectl apply -k chaos/scenarios/level-2-kubernetes/ui-bad-deploy/inject
```

## Observe

- **Error ratio (5xx) by service**: only `ui`. Do catalog, carts and orders still look healthy?
- A blue **Rollouts** marker just before the errors start.
- **Pods ready** and **Container restarts**: anything unusual?

## Diagnose

- What changed? `kubectl -n retail-store rollout history deploy/ui`
- Compare two revisions: `kubectl -n retail-store rollout history deploy/ui --revision=<n>`
- `kubectl -n retail-store logs deploy/ui --tail=100` - which call fails, and to what host?
- Does catalog itself answer? `kubectl -n retail-store get endpoints catalog`

## Recover

Roll back to the previous revision:

```bash
kubectl -n retail-store rollout undo deploy/ui
```

Or re-apply the good release (what `scripts/chaos.py recover` does):

```bash
kubectl apply -k chaos/scenarios/level-2-kubernetes/ui-bad-deploy/recover
```

## Verify

Retail Store dashboard: UI error ratio ~0%, orders/min > 0, all pods ready. The store shows products again.
`kubectl -n retail-store rollout history deploy/ui` shows a new revision with the good configuration.

<details>
<summary>Solution (open after you tried)</summary>

The release overrides `RETAIL_UI_ENDPOINTS_CATALOG` with `http://catalog-api`, a host name that does not exist.
The readiness probe does not check dependencies, so the broken pod is `Ready` and the rollout "succeeds".

A restart creates new pods from the same broken template. A `rollout restart` even adds a new revision,
so a later `rollout undo` goes back to the broken revision before it. Then use
`kubectl -n retail-store rollout undo deploy/ui --to-revision=<last good>`.

Lesson: the first question in an incident is "what changed?". A rollout marker right before the errors points at a rollback, not a restart.
A real fix is a safer rollout: more than 1 replica, a readiness check that catches bad config, and automatic rollback on errors.

</details>
