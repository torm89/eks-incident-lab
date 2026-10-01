# torm-eks

A sandbox for practicing incident response on Amazon EKS.

## Goal

1. **Provision** a test EKS cluster.
2. **Deploy** a fake application to the cluster.
3. **Generate** synthetic traffic against the application.
4. **Inject** a failure into the system.
5. **Detect and handle** the failure.

## Repository layout

| Path                     | Purpose                                              |
|--------------------------|------------------------------------------------------|
| `infra/`                 | Terraform root module: wires network and EKS together |
| `infra/modules/network/` | Child module: VPC, subnets, NAT gateway              |
| `infra/modules/eks/`     | Child module: EKS cluster and node group             |

More directories (application, traffic generator, chaos scenarios) will be added as the project grows.

## Requirements

- Python >= 3.12
- Terraform
- AWS CLI with configured credentials
- kubectl

## Create the cluster

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars   # set your IP in api_allowed_cidrs
terraform init
terraform apply
$(terraform output -raw configure_kubectl)
kubectl get nodes
```

Defaults: region `eu-central-1`, Kubernetes 1.36, 2 spot `t3.medium` nodes, single NAT gateway.

## Warning

This repo creates real AWS resources that cost money.
Always destroy everything when you are done:

```bash
cd infra && terraform destroy
```
