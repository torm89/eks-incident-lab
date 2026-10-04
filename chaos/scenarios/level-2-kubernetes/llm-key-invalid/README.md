# llm-key-invalid

**Level:** 2 - Kubernetes &nbsp;|&nbsp; **Tool:** `kubectl apply` (a changed Secret) &nbsp;|&nbsp; **Needs:** `apps/ai-assistant` (mock mode, llm-gateway >= 0.2.0) + `traffic/ai-assistant`

A key rotation goes wrong: the `anthropic-api-key` Secret gets a malformed key. Nothing is deployed, no pod restarts.

> [!WARNING]
> Practice this in **mock mode**. In real mode inject overwrites your real key in the Secret, and recover puts a
> placeholder there: create the Secret again with your key afterwards (`apps/ai-assistant/README.md`).

## Hypothesis

About a minute after the change, every chat question fails with 503. The LLM answers HTTP 401 and the SDK does not retry it.
Restarting the gateway or the assistant does not help: they read the same Secret again.

## Inject

```bash
kubectl apply -k chaos/scenarios/level-2-kubernetes/llm-key-invalid/inject
```

## Observe

- **Incident Lab / AI Assistant** → **Errors** and **Questions / s by outcome**: `llm_error`.
- **LLM calls / s by result**: which `error_type`?
- **Retry amplification**: compare with `llm-rate-limit`. Why is it different?
- Is there a **Rollouts** marker before the errors?

## Diagnose

- `kubectl -n ai-assistant logs deploy/ai-assistant --tail=50` - what does the LLM answer?
- `kubectl -n ai-assistant logs deploy/llm-gateway --tail=50` - status codes of the calls.
- Nothing was deployed, so what changed? `kubectl -n ai-assistant get secret anthropic-api-key -o yaml`:
  look at `managedFields[].time`, and decode the key (`base64 -d`). Does it look like an Anthropic key (`sk-ant-...`)?

## Recover

Put a valid key back into the Secret. In mock mode any well-formed key works:

```bash
kubectl apply -k chaos/scenarios/level-2-kubernetes/llm-key-invalid/recover
```

In real mode, your own key:

```bash
kubectl -n ai-assistant create secret generic anthropic-api-key --from-literal=api-key=<your key> --dry-run=client -o yaml | kubectl apply -f -
```

No restart needed: the gateway picks up the new key within about a minute.

## Verify

AI Assistant dashboard: errors ~0%, **LLM calls / s by result** only successful calls, answers flowing again.

<details>
<summary>Solution (open after you tried)</summary>

The new key lost its `sk-` prefix in copy and paste. The LLM API answers **401 authentication_error** to every call.
401 is not retried by the SDK (only 408, 409, 429 and 5xx are), so there is no retry amplification: the calls fail fast.

The gateway mounts the Secret as a file and re-reads it on every request. The kubelet updated the file about a minute
after the Secret changed: the failure started with **no rollout and no restart**. A restart reads the same bad file.

Lesson: "nothing was deployed" does not mean "nothing changed". Configuration and secrets change outside the
deploy pipeline. Check when they changed, and fix the source, not the pods.
With an environment variable instead of a file, the bad key would only bite at the next restart, maybe days later.

</details>
