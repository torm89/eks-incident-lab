# catalog-network-policy

**Level:** 2 - Kubernetes &nbsp;|&nbsp; **Tool:** `kubectl apply` (a NetworkPolicy) &nbsp;|&nbsp; **Needs:** NetworkPolicy enforcement in the VPC CNI (`infra/`, on by default)

A security hardening change adds a NetworkPolicy: "only the UI may call the catalog". It has a bug.

## Hypothesis

Product pages get slow, then fail. Every pod stays `Running` and `Ready`, nothing restarts.
Restarting the catalog or the UI does not help: the network path is blocked, not the pods.

## Inject

```bash
kubectl apply -k chaos/scenarios/level-2-kubernetes/catalog-network-policy/inject
```

## Observe

- **Error ratio (5xx) by service** and **Latency by service**: which service fails, and is it slow first?
- **Requests / s by service**: what happens to the catalog line?
- With the AI assistant: **Tool calls / s by tool and outcome** on the AI Assistant dashboard.

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

Retail Store dashboard: UI error ratio ~0%, latency back to normal, the catalog line back in **Requests / s by service**.
The AI assistant's tools succeed again.

<details>
<summary>Solution (open after you tried)</summary>

The policy selects the catalog pods, so from now on only the traffic it allows can reach them.
It allows pods labelled `app: ui`, but the UI pods are labelled `app.kubernetes.io/name: ui`. The selector matches
nothing: **all** traffic to the catalog is denied. The UI, the AI assistant's tools and Prometheus are all cut off.

Denied packets are dropped, not rejected: callers wait for their timeout. That is why the UI gets slow before it fails.
The catalog's own metrics stop too, because Prometheus cannot scrape it: a gap in a panel is a symptom, not "no traffic".
Probes come from the node, which NetworkPolicy always allows, so the pods stay `Ready`.

Lesson: when healthy pods cannot talk to each other, check the network layer: NetworkPolicies, Services and endpoints, DNS.
Test a policy before rollout: list the pods its selectors match, and the callers it leaves out.

</details>
