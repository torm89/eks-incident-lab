# catalog-db-pod-kill

**Level:** 2 - Kubernetes &nbsp;|&nbsp; **Tool:** Chaos Mesh `PodChaos`

The catalog MySQL pod is killed once. Its data lives in an `emptyDir` volume.

## Hypothesis

MySQL restarts within a minute, but empty. The catalog keeps failing even though every pod is `Running`.

## Inject

```bash
kubectl apply -k chaos/scenarios/catalog-db-pod-kill/inject
```

## Observe

- **Ready pods** dips briefly.
- **5xx errors / s**: `ui`. Does it go back to zero by itself?
- **Container restarts** for `catalog-mysql-0`.

## Diagnose

- `kubectl -n retail-store get pods` - everything `Running`?
- `kubectl -n retail-store logs deploy/catalog` - what does catalog say about the database?
- Open the store: is the product list empty?

## Recover

```bash
kubectl -n retail-store rollout restart deploy/catalog
```

```bash
kubectl delete -k chaos/scenarios/catalog-db-pod-kill/inject
```

## Verify

Retail Store dashboard: requests flowing, UI error ratio ~0%, orders/min > 0, all pods ready. The store shows products again.

<details>
<summary>Solution (open after you tried)</summary>

MySQL came back with an empty data directory. The catalog creates its schema and sample data only at startup, so it must be restarted.

Lesson: "all pods Running" does not mean "working". A real fix is persistent storage (EBS + PVC) for the database.

</details>
