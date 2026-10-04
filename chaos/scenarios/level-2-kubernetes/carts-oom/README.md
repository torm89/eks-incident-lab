# carts-oom

**Level:** 2 - Kubernetes &nbsp;|&nbsp; **Tool:** `kubectl apply` (a bad release)

A cost-cutting release lowers the carts memory limit far below what the service needs.

## Hypothesis

The carts pod is killed again and again and never becomes ready. The cart and checkout fail; browsing still works.
Restarting does not help: every new pod gets the same limit.

## Inject

```bash
kubectl apply -k chaos/scenarios/level-2-kubernetes/carts-oom/inject
```

## Observe

- **Error ratio (5xx) by service**: `ui` and `carts`. Does the home page still load?
- **Pods ready**: carts drops out. **Container restarts (15 min)** keeps growing.
- **Memory, % of limit** for carts: does it reach 100%?

## Diagnose

- `kubectl -n retail-store get pods -l app.kubernetes.io/name=carts` - status and restart count?
- `kubectl -n retail-store describe pod -l app.kubernetes.io/name=carts` - look at **Last State**: reason and exit code.
- `kubectl -n retail-store get deploy carts -o jsonpath='{.spec.template.spec.containers[0].resources}'`
- What changed? `kubectl -n retail-store rollout history deploy/carts`

## Recover

Raise the limit back to what carts needs:

```bash
kubectl -n retail-store set resources deploy/carts --requests=memory=512Mi --limits=memory=512Mi
```

Or re-apply the good release (what `scripts/chaos.py recover` does):

```bash
kubectl apply -k chaos/scenarios/level-2-kubernetes/carts-oom/recover
```

## Verify

Retail Store dashboard: carts ready, restarts stop growing, UI error ratio ~0%, orders/min > 0.
Memory of carts stays well below 100% of its limit.

<details>
<summary>Solution (open after you tried)</summary>

The release sets the carts memory limit to 128Mi instead of 512Mi.
The JVM sizes its heap to 75% of the limit (`-XX:MaxRAMPercentage=75.0`) and needs native memory on top of it.
The container goes over the limit and the kernel kills it: **Last State: Terminated, Reason: OOMKilled, Exit Code: 137**.
Kubernetes restarts it with a growing delay: `CrashLoopBackOff`.

If the reason is `Error` (exit code 1) instead, the JVM itself ran out of heap (`java.lang.OutOfMemoryError` in
`kubectl logs --previous`). Same cause, same fix.

The rollout never finishes (`kubectl rollout status` hangs). With 1 replica and `maxUnavailable: 1` the old, healthy pod
was removed before the new one was ready: the outage starts with the rollout.

Lesson: OOMKilled is not a bug to restart away. Read the last state and exit code, then fix the limit at its source
(here: the manifests). `kubectl rollout undo` also works; it is the fastest way to stop the bleeding.
Size limits from measured usage (**Memory, % of limit**), not from a cost target.

</details>
