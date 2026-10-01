# torm-eks

A sandbox for practicing incident response on Amazon EKS.

## Goal

1. **Provision** a test EKS cluster.
2. **Deploy** a fake application to the cluster.
3. **Generate** synthetic traffic against the application.
4. **Inject** a failure into the system.
5. **Detect and handle** the failure.

## Repository layout

| Path     | Purpose                                  |
|----------|------------------------------------------|
| `infra/` | Terraform code for the AWS / EKS infra   |

More directories (application, traffic generator, chaos scenarios) will be added as the project grows.

## Requirements

- Python >= 3.12
- Terraform
- AWS CLI with configured credentials
- kubectl

## Warning

This repo creates real AWS resources that cost money.
Always destroy the cluster when you are done:

```bash
cd infra && terraform destroy
```
