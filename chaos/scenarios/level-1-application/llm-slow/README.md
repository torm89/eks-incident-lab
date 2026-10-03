# llm-slow

**Level:** 1 - application &nbsp;|&nbsp; **Tool:** chaos API &nbsp;|&nbsp; **Needs:** `apps/ai-assistant` + `traffic/ai-assistant`

Every LLM call gets 20 seconds of extra delay, like when the provider is overloaded.

## Hypothesis

Answers still succeed, but each one takes about 40 s (two LLM calls per answer). No errors, so nothing is red.

## Inject

```bash
kubectl create -k chaos/scenarios/level-1-application/llm-slow/inject
```

## Observe

- **LLM latency (successful calls)** and **Latency p95 by outcome** jump.
- **Questions / s by outcome**: still `success`?
- `kubectl -n traffic logs deploy/ai-load-generator` - response times.

## Diagnose

- Is it the LLM or a tool? Compare **LLM latency** with **Tool latency p95 by tool**.
- How many LLM calls per answer? (**Agent steps per answer**)
- What happens if the delay is longer than the SDK timeout (30 s)? Try `/chaos/latency/35000`.

## Recover

```bash
kubectl create -k chaos/scenarios/level-1-application/llm-slow/recover
```

## Verify

AI Assistant dashboard: chat error ratio ~0%, LLM calls all `success`, p95 chat latency back to normal.

<details>
<summary>Solution (open after you tried)</summary>

Latency of an agent = sum of all its LLM and tool calls. Two slow LLM calls make one very slow answer.

With a delay above the 30 s SDK timeout, every call times out and is retried twice: ~90 s until a 503. Retries make a slow provider much worse.

Lessons: stream answers so users see progress, set timeouts per step, limit retries for interactive requests, alert on p95 latency, not only on errors.

</details>
