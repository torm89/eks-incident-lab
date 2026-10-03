# ai-tool-cascade

**Level:** 1 - application &nbsp;|&nbsp; **Tool:** chaos API &nbsp;|&nbsp; **Needs:** `apps/ai-assistant` + `traffic/ai-assistant`

The catalog (a tool of the assistant) gets 6 seconds of delay, longer than the assistant's 5 s tool timeout. The LLM itself is healthy.

## Hypothesis

The store gets slow. The assistant keeps answering with HTTP 200, but its answers are useless: the tools fail and the AI has no products to talk about.

## Inject

```bash
kubectl create -k chaos/scenarios/level-1-application/ai-tool-cascade/inject
```

## Observe

- **Tool calls / s by tool and outcome**: `error` appears.
- **Chat requests / s by outcome**: still `success`!
- **Retail Store** dashboard: the whole store is slow too.
- Ask the assistant yourself and read the answer.

## Diagnose

- `kubectl -n ai-assistant port-forward svc/ai-assistant 8081:80`, then `curl -X POST localhost:8081/chat -H 'content-type: application/json' -d '{"message":"gifts under 50?"}'`
- Which dependency is slow? The LLM or the catalog?
- Why does the chat error ratio stay at 0%?

## Recover

```bash
kubectl create -k chaos/scenarios/level-1-application/ai-tool-cascade/recover
```

## Verify

AI Assistant dashboard: chat error ratio ~0%, LLM calls all `success`, p95 chat latency back to normal. Tool calls all `success`.

<details>
<summary>Solution (open after you tried)</summary>

This is a silent failure: HTTP 200, but the answer is wrong or empty. Status codes alone cannot catch it.

The root cause is in the catalog, not in the AI. Fix the catalog (recover step, or restart `deploy/catalog`).

Lessons: monitor tool error rates, mark answers built on failed tools, alert on quality signals, not only on HTTP status. With the real API, Claude may also apologise or guess - read the answers.

</details>
