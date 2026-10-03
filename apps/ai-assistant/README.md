# AI shopping assistant

A chat assistant for the Retail Store, built with the [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python).
Customers ask questions; Claude (Haiku 4.5) answers using tools that query the store catalog.

```
customer ──► ai-assistant ──► llm-gateway ──► mock (default, free)
                 │                       └──► Anthropic API (real-api overlay, paid)
                 └──► catalog (tools: search_products, get_product, list_tags)
```

| Component | Source | What it does |
|---|---|---|
| `ai-assistant` | [services/ai-assistant](../../services/ai-assistant) | `POST /chat`. Agent loop with a hard step limit. Metrics: tokens, cost, latency, LLM and tool outcomes. |
| `llm-gateway` | [services/llm-gateway](../../services/llm-gateway) | Proxy in front of the Messages API. Holds the only copy of the API key. `/chaos/*` API to inject 4xx/5xx and latency. |

> [!IMPORTANT]
> The gateway runs in **mock mode by default**: answers are generated locally, no API key, **no cost**.
> The dashboard still shows the cost the real API *would* have.

## Deploy

Needs the cluster, the Retail Store (`apps/retail-store`) and the images in ECR.

```bash
uv run scripts/push_images.py           # build + push both images, write image references (once per cluster)
kubectl apply -k apps/ai-assistant/base
kubectl -n ai-assistant get pods
```

Try it:

```bash
kubectl -n ai-assistant port-forward svc/ai-assistant 8081:80
curl -X POST localhost:8081/chat -H "content-type: application/json" -d '{"message": "What gifts do you have under 50 dollars?"}'
```

Generate traffic (one question every 10 s):

```bash
kubectl apply -k traffic/ai-assistant
```

Grafana dashboard: **Incident Lab / AI Assistant**.

## Real Anthropic API (paid)

1. Create the Secret from your key. The key never goes into the repo.

   ```bash
   kubectl -n ai-assistant create secret generic anthropic-api-key --from-literal=api-key=<your key>
   ```

2. Switch the gateway to real mode:

   ```bash
   kubectl apply -k apps/ai-assistant/overlays/real-api
   ```

3. Back to mock mode (free):

   ```bash
   kubectl apply -k apps/ai-assistant/base
   ```

Cost with Claude Haiku 4.5 ($1 / $5 per million input / output tokens) and the default AI traffic
(one question every 10 s, two LLM calls per answer): roughly **$1-2 per hour**.
Watch **LLM cost / hour** on the dashboard and stop the traffic when you are done:

```bash
kubectl delete -k traffic/ai-assistant
```

## Chaos scenarios

See [chaos/README.md](../../chaos/README.md): `llm-rate-limit`, `llm-slow`, `ai-tool-cascade`.

## Change the code

```bash
cd services/ai-assistant      # or services/llm-gateway
uv sync
uv run pytest
```

Check that the images still build, without AWS (no login, no push):

```bash
uv run scripts/push_images.py --build-only
```

After a change: bump `version` in the service's `pyproject.toml`, then run `uv run scripts/push_images.py`.
The script pushes the new tag and regenerates `apps/ai-assistant/registry/` (git-ignored image references
for your AWS account). Apply `apps/ai-assistant/base` again to roll it out.
