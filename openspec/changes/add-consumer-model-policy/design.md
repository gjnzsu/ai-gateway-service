## Context

`ai-gateway-service` now extracts `X-Consumer-Service`, emits structured logs, and sends LLM metrics to the observability service. Consumer model policy can use the same consumer identity to evaluate requested models.

This phase intentionally evaluates and logs policy decisions only. Enforcement would be a later, explicit migration because blocking model access can break existing services.

## Goals / Non-Goals

**Goals:**
- Read consumer policy from `config.yaml`.
- Support a `default` policy for unknown or missing consumers.
- Evaluate requested model aliases before provider calls.
- Add policy fields to structured chat completion logs.
- Keep all policies in `log_only` behavior for this phase.
- Preserve compatibility for no-header requests and `ai-market-studio`.

**Non-Goals:**
- Block requests.
- Add auth, JWT, API keys, or Kong consumer mapping.
- Add quotas, budgets, or per-user policy.
- Dynamically reload policy without restart.
- Change `/v1/models` output.

## Decisions

1. **Policy is keyed by consumer service name.**
   - The gateway already supports optional `X-Consumer-Service`.
   - Missing header maps to `unknown`, which uses the `default` policy.

2. **Policy uses model aliases, not provider model names.**
   - Consumers request aliases such as `gpt-4o-mini`.
   - Policy remains stable even if provider mapping changes later.

3. **Only `log_only` mode is active.**
   - The config can declare `mode: log_only`.
   - Any other mode is treated as `log_only` in this phase to avoid accidental enforcement.

4. **Policy result is attached to existing structured logs.**
   - Fields: `policy_mode`, `policy_allowed`, `policy_reason`.
   - This gives immediate signal in logs and prepares later metrics.

## Risks / Trade-offs

- [Risk] Missing consumer headers reduce policy precision. -> Mitigation: default policy is explicit and logs consumer as `unknown`.
- [Risk] Operators might assume policy blocks traffic. -> Mitigation: README and spec state this phase is log-only.
- [Risk] Policy config drift could surprise future enforcement. -> Mitigation: tests cover known and unknown consumer behavior now.
