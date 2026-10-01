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
| `infra/`                 | OpenTofu root module: wires network and EKS together |
| `infra/modules/network/` | Child module: VPC, subnets, NAT gateway              |
| `infra/modules/eks/`     | Child module: EKS cluster and node group             |
| `apps/retail-store/`     | Kustomize: EKS Workshop Retail Store Sample App      |
| `traffic/`               | Kustomize: Artillery load generator for the app      |
| `platform/monitoring/`   | Kustomize + Helm: Prometheus and Grafana             |

More directories (chaos scenarios) will be added as the project grows.

## Requirements

- Python >= 3.12
- OpenTofu >= 1.10
- AWS CLI with the `<aws-profile>` profile configured
- kubectl
- Helm 3 (kubectl's built-in kustomize does not work with Helm 4)

## Create the cluster

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars   # set your IP in api_allowed_cidrs
tofu init
tofu apply
$(tofu output -raw configure_kubectl)
kubectl get nodes
```

Defaults: region `eu-west-1`, Kubernetes 1.36, 2 spot `t3.medium` nodes, single NAT gateway.

State is stored in S3 bucket `<state-bucket>` (key `infra/terraform.tfstate`) with a lock file.

## Deploy monitoring

[kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
in namespace `monitoring`. CRDs go first, so the stack's custom resources can be created.

```bash
kubectl kustomize --enable-helm platform/monitoring/crds | kubectl apply --server-side -f -
kubectl kustomize --enable-helm platform/monitoring | kubectl apply --server-side -f -
kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80   # open http://localhost:3000
```

Grafana has no login (it is reachable only via port-forward). Open dashboard **Retail Store**.

## Deploy the application

The [Retail Store Sample App](https://github.com/aws-containers/retail-store-sample-app) (pinned release) runs in namespace `retail-store`.

```bash
kubectl apply -k apps/retail-store
kubectl -n retail-store get pods
kubectl -n retail-store port-forward svc/ui 8080:80   # open http://localhost:8080
```

## Generate traffic

An [Artillery](https://www.artillery.io/) Deployment runs the upstream shopper scenario
(browse catalog, add to cart, checkout) against `http://ui.retail-store.svc`.

```bash
kubectl apply -k traffic
kubectl -n traffic logs -f deploy/load-generator             # live stats every 10 s
kubectl -n traffic scale deploy/load-generator --replicas=3  # more load
kubectl delete -k traffic                                    # stop
```

Load knobs in `traffic/load-generator.yaml`: `replicas` and `arrivalRate` (new users per second, per replica).

## Warning

This repo creates real AWS resources that cost money.
Always destroy everything when you are done:

```bash
cd infra && tofu destroy
```
