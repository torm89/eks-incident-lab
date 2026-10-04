# catalog-db-pod-kill

**Level:** 2 - Kubernetes &nbsp;|&nbsp; **Tool:** Chaos Mesh `PodChaos`

The catalog MySQL pod is killed once. Its data lives in an `emptyDir` volume.

## Hypothesis

MySQL restarts within a minute, but empty. The catalog keeps failing even though every pod is `Running`.

## Inject

```bash
kubectl apply -k chaos/scenarios/level-2-kubernetes/catalog-db-pod-kill/inject
```

## Observe

- **Errors**: most UI requests fail. Does it go back to zero by itself?
- **Error ratio (5xx) by service**: only `ui`. Why does `catalog` stay at 0%?
- **Pods ready** and **Container restarts**: anything at all? The new MySQL pod is usually ready within seconds.
- **Requests / s by service**: catalog still gets traffic. What does it answer?

## Diagnose

- `kubectl -n retail-store get pods` - everything `Running`?
- `kubectl -n retail-store logs deploy/catalog` - what does catalog say about the database?
- Open the store: is the product list empty?

## Recover

```bash
kubectl -n retail-store rollout restart deploy/catalog
```

```bash
kubectl delete -k chaos/scenarios/level-2-kubernetes/catalog-db-pod-kill/inject
```

## Verify

Retail Store dashboard: requests flowing, UI error ratio ~0%, orders/min > 0, all pods ready. The store shows products again.

<details>
<summary>Solution (open after you tried)</summary>

MySQL came back with an empty data directory. The catalog creates its schema and sample data only at startup, so it must be restarted.

The catalog logs `Table 'catalog.products' doesn't exist` but answers **404 Not Found**, not 5xx: from its point of view the
products just do not exist. The UI turns that into 5xx. The MySQL pod is replaced within seconds, so no restart and
usually no `DataStoreNotReady`: nothing on the Kubernetes side looks wrong.

Lesson: "all pods Running" does not mean "working". A real fix is persistent storage (EBS + PVC) for the database.

</details>
