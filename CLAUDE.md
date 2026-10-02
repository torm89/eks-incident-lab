# CLAUDE.md

## Project purpose

This repo is a sandbox for incident-response practice on EKS:

1. Provision a test EKS cluster.
2. Deploy a fake application.
3. Generate synthetic traffic.
4. Inject a failure.
5. Detect and handle the failure.

## Rules

- **English only** in all code, comments, commit messages, file names and docs inside the repo.
- Follow **clean code** principles: meaningful names, small single-purpose functions/modules, no dead code, no magic values, DRY.
- **Infrastructure as code** lives in OpenTofu (>= 1.10, use `tofu`, not `terraform`). Do not create AWS resources by hand or via scripts. OpenTofu root modules:
  - `infra/` - the environment (network, EKS).
  - `chaos/scenarios/<name>/infra/` - one AWS FIS experiment template per scenario, with its own IAM role (shared module `chaos/modules/fis-role`) and state key `chaos/<name>/terraform.tfstate`. Targets are found by tags, never by IDs from `infra/` state.
- `infra/` is a single root module (one state in S3 bucket `<state-bucket>`, locked with `use_lockfile`). `infra/main.tf` wires child modules together through their outputs:
  - `infra/modules/network/` - VPC, subnets, NAT gateway.
  - `infra/modules/eks/` - EKS cluster and node group.
  - Defaults live in the root `variables.tf`. Child module variables have no defaults.
- Nothing that runs inside the cluster is managed by OpenTofu. Kubernetes objects are plain Kustomize, applied with kubectl, so destroying the cluster leaves no stale state.
- AWS access goes through the `<aws-profile>` profile (account <account-id>, region eu-west-1).
- Base cluster components (always installed) live in `platform/<name>/` as Kustomize with `helmCharts` (pinned chart version + `values.yaml`).
  - Build with `kubectl kustomize --enable-helm`, apply with `kubectl apply --server-side` (large CRDs). Requires Helm 3.
  - CRDs are a separate kustomization (`crds/`), applied first.
  - Helm hooks are not executed: disable chart features that depend on them.
- Kubernetes apps live in `apps/<name>/` as Kustomize bases.
  - Third-party apps are referenced by a pinned release URL, never copied into the repo. Our changes go into `patches/`.
- Grafana dashboards live in `platform/monitoring/dashboards/*.json`, generated as ConfigMaps labelled `grafana_dashboard: "1"`. `apps/` holds only the app and its patches.
- Everything for failure injection lives in `chaos/`. Chaos tooling is optional and installed only when practicing.
  - `chaos/chaos-mesh/` - Chaos Mesh engine (same pattern as `platform/`: `crds/` first, then Helm via Kustomize).
  - `chaos/base/` - shared Job that calls the app's built-in `/chaos/*` API.
  - `chaos/scenarios/<name>/` - one folder per scenario: `README.md` (hypothesis, observe, diagnose, recover, verify, hidden solution) plus `inject/` + `recover/` (Kustomize) or `infra/` (OpenTofu, AWS FIS).
- Synthetic traffic lives in `traffic/` (Kustomize, namespace `traffic`). The scenario image tag must match the app release in `apps/retail-store/`.
- Python code targets Python >= 3.12 (see `pyproject.toml`).
- Keep costs low: this is a test cluster. Prefer small instance types and make teardown (`tofu destroy`) easy.
- Never commit secrets, state files or `.tfvars` with real credentials.
