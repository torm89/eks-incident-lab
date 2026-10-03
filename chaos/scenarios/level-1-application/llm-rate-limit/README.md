# llm-rate-limit

**Level:** 1 - application &nbsp;|&nbsp; **Tool:** chaos API &nbsp;|&nbsp; **Needs:** `apps/ai-assistant` + `traffic/ai-assistant`

The LLM API starts answering every request with HTTP 429 (rate limit), like when you exceed your Anthropic quota.

## Hypothesis

Every chat request fails with 503. The SDK retries each LLM call, so the gateway sees about 3 times more requests than the assistant makes.

## Inject

```bash
kubectl create -k chaos/scenarios/level-1-application/llm-rate-limit/inject
```

## Observe

- **AI Assistant** dashboard: **LLM calls / s by result** shows `429`.
- Golden signal **Errors** goes to 100%.
- **Retry amplification** rises above 1: the gateway gets more requests than the assistant makes LLM calls. Where does the difference come from?

## Diagnose

- `kubectl -n ai-assistant logs deploy/ai-assistant`
- Which side returns 429: our code, the gateway, or the API behind it?
- How many retries does the SDK make, and how long does it wait between them?

## Recover

```bash
kubectl create -k chaos/scenarios/level-1-application/llm-rate-limit/recover
```

## Verify

AI Assistant dashboard: chat error ratio ~0%, LLM calls all `success`, p95 chat latency back to normal.

<details>
<summary>Solution (open after you tried)</summary>

The 429 comes from the LLM provider (here: the gateway). Our code cannot fix the quota, it can only react well:

- The SDK retries 2 times (`max_retries`) and respects `retry-after`. Retries multiply the load on an already limited API.
- Better: fewer calls (caching answers to common questions), a queue with backoff, a clear "try again later" message, a higher quota.

Recover with the recover step. In a real incident: check the provider console for rate limits, lower traffic, or wait.

</details>
