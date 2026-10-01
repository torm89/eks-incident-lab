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
- **Infrastructure as code** lives in OpenTofu (>= 1.10, use `tofu`, not `terraform`), in the `infra/` directory. Do not create AWS resources by hand or via scripts outside `infra/`.
- `infra/` is a single root module (one state in S3 bucket `<state-bucket>`, locked with `use_lockfile`). `infra/main.tf` wires child modules together through their outputs:
  - `infra/modules/network/` - VPC, subnets, NAT gateway.
  - `infra/modules/eks/` - EKS cluster and node group.
  - Defaults live in the root `variables.tf`. Child module variables have no defaults.
- Resources running inside the cluster (Helm charts, Kubernetes objects) go into a separate root module with its own state, never into `infra/` root. Kubernetes/Helm providers need an existing cluster.
- AWS access goes through the `<aws-profile>` profile (account <account-id>, region eu-west-1).
- Kubernetes apps live in `apps/<name>/` as Kustomize bases.
  - Third-party apps are referenced by a pinned release URL, never copied into the repo. Our changes go into `patches/`.
- Synthetic traffic lives in `traffic/` (Kustomize, namespace `traffic`). The scenario image tag must match the app release in `apps/retail-store/`.
- Python code targets Python >= 3.12 (see `pyproject.toml`).
- Keep costs low: this is a test cluster. Prefer small instance types and make teardown (`tofu destroy`) easy.
- Never commit secrets, state files or `.tfvars` with real credentials.
