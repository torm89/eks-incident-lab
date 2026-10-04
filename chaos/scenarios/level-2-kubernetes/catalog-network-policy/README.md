# catalog-network-policy

**Level:** 2 - Kubernetes &nbsp;|&nbsp; **Tool:** `kubectl apply` (a NetworkPolicy) &nbsp;|&nbsp; **Needs:** NetworkPolicy enforcement in the VPC CNI (`infra/`, on by default)

A security hardening change adds a NetworkPolicy: "only the UI may call the catalog". It has a bug.

## Hypothesis

At first almost nothing happens: the store keeps working, only the AI assistant's tools fail.
The policy blocks new connections, and the UI reuses connections it opened before. Over the next minutes the UI
renews them, and errors creep in. Every pod stays `Running` and `Ready`.

Restarting the UI makes it **worse**: the new pod has to open new connections, and the whole store goes down.

## Inject

```bash
kubectl apply -k chaos/scenarios/level-2-kubernetes/catalog-network-policy/inject
```

## Observe

- With the AI assistant: **Tool calls / s by tool and outcome** on the AI Assistant dashboard. This fails first.
- **Error ratio (5xx) by service**: does the store notice at all? Watch it for 5-10 minutes.
- Then try what many would do first: `kubectl -n retail-store rollout restart deploy/ui`. What happens to **Traffic**?

## Diagnose

- `kubectl -n retail-store get pods` - all `Running` and `Ready`?
- `kubectl -n retail-store logs deploy/ui --tail=100` - errors calling the catalog: refused or timed out?
- Does the catalog answer when you go straight to its pod (port-forward comes through the node)?
  `kubectl -n retail-store port-forward deploy/catalog 8090:8080`, then open `http://localhost:8090/health`.
- And from another pod?
  `kubectl -n retail-store run net-test --rm -it --restart=Never --image=busybox -- wget -T 3 -qO- http://catalog/health`
- What controls traffic between pods? `kubectl get networkpolicy -A`, then `kubectl -n retail-store describe networkpolicy <name>`.
  Which pods does its `from` selector match? `kubectl -n retail-store get pods -l <selector>`

## Recover

Delete the policy:

```bash
kubectl delete -k chaos/scenarios/level-2-kubernetes/catalog-network-policy/inject
```

Or fix its selector to the real UI labels (`app.kubernetes.io/name: ui`) and allow the other callers too.

## Verify

Retail Store dashboard: traffic back to normal, UI error ratio ~0%, latency back to normal.
The AI assistant's tools succeed again.

<details>
<summary>Solution (open after you tried)</summary>

The policy selects the catalog pods, so from now on only the traffic it allows can reach them.
It allows pods labelled `app: ui`, but the UI pods are labelled `app.kubernetes.io/name: ui`. The selector matches
nothing: **all new** traffic to the catalog is denied.

The VPC CNI enforces policies on new connections; connections that were open before the policy keep working.
The UI and Prometheus keep their keep-alive connections, so the store and the catalog metrics look fine for a while.
The AI assistant opens a new connection per tool call: it fails at once (`AssistantToolQualityBudgetBurnFast`).
A UI restart drops the old connections. The new ones hang (denied packets are dropped, not rejected), the UI receives
almost no requests, and the store SLOs see nothing: only `StoreTrafficLost` fires.
Probes come from the node, which NetworkPolicy always allows, so the pods stay `Ready`.

A latent failure like this one waits for the next restart, deploy or node replacement, maybe hours after the change.

Lesson: "what changed recently?" includes changes that have not bitten yet. A restart is not a harmless first step.
When healthy pods cannot talk to each other, check the network layer: NetworkPolicies, Services and endpoints, DNS.
Test a policy before rollout: list the pods its selectors match, and the callers it leaves out.

</details>
