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
- **Infrastructure as code** lives in Terraform, in the `infra/` directory. Do not create AWS resources by hand or via scripts outside `infra/`.
- Each subdirectory of `infra/` is a separate Terraform root module with its own state:
  - `infra/eks/` - VPC and EKS cluster.
  - Resources running inside the cluster (Helm charts, Kubernetes objects) go into a separate root (e.g. `infra/addons/`), never into `infra/eks/`.
- Python code targets Python >= 3.12 (see `pyproject.toml`).
- Keep costs low: this is a test cluster. Prefer small instance types and make teardown (`terraform destroy`) easy.
- Never commit secrets, Terraform state files or `.tfvars` with real credentials.
