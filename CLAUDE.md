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
  - `chaos/scenarios/level-3-aws/<name>/infra/` - one AWS FIS experiment template per scenario, with its own IAM role (shared module `chaos/modules/fis-role`) and state key `chaos/<name>/terraform.tfstate`. Targets are found by tags, never by IDs from `infra/` state.
- `infra/` is a single root module (one state in S3 bucket `<state-bucket>`, locked with `use_lockfile`). `infra/main.tf` wires child modules together through their outputs:
  - `infra/modules/network/` - VPC, subnets, NAT gateway (only when `node_subnet_type = "private"`).
  - `node_subnet_type` (`public` default, or `private`) decides where worker nodes run. Subnets hosting nodes are tagged `NodeSubnet=true`: use that tag (not public/private tags) to target nodes' subnets, e.g. in FIS.
  - `infra/modules/eks/` - EKS cluster and node group.
  - `infra/modules/registry/` - ECR repositories for our own service images (`services/`). Created and destroyed with the environment.
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
  - `chaos/scenarios/level-<n>-<layer>/<name>/` - scenarios grouped by level: `level-1-application` (built-in chaos API), `level-2-kubernetes` (Chaos Mesh), `level-3-aws` (AWS FIS). Each has `README.md` (hypothesis, observe, diagnose, recover, verify, hidden solution) plus `inject/` + `recover/` (Kustomize) or `infra/` (OpenTofu).
- Our own services live in `services/<name>/` (Python >= 3.12, `uv`, `src/` layout, `pytest` tests, `Dockerfile` with a numeric non-root user).
  - The image tag is the `version` in the service's `pyproject.toml`. It must match `newTag` in `apps/ai-assistant/base/kustomization.yaml`; `scripts/push_images.py` builds, checks and pushes to ECR.
  - Run `uv run pytest` in the service directory after every change.
- AI assistant (`apps/ai-assistant/`): `base/` (mock LLM, default, free) and `overlays/real-api/` (paid Anthropic API).
  - Model: `claude-haiku-4-5` (chosen by the user for cost). Only `llm-gateway` holds the API key (Secret `anthropic-api-key`, created by hand, never in the repo).
  - `llm-gateway` exposes the same `/chaos/status` and `/chaos/latency` contract as the Retail Store, so AI scenarios reuse `chaos/base`.
- Synthetic traffic lives in `traffic/` (Kustomize, namespace `traffic`); AI questions in `traffic/ai-assistant/` (apply after `traffic/`). The scenario image tag must match the app release in `apps/retail-store/`.
- Python code targets Python >= 3.12 (see `pyproject.toml`).
- Keep costs low: this is a test cluster. Prefer small instance types and make teardown (`tofu destroy`) easy.
- Never commit secrets, state files or `.tfvars` with real credentials.
