## Why

The gateway already logs prompt-injection and sensitive-data signals, but it does not mask PII or enforce prompt/response safety policy. AI Market Studio needs the gateway to provide a real safety boundary before and after provider calls without relying on Kong Enterprise AI plugins.

## What Changes

- Extend `security_checks` into configurable AI guardrails with `log_only`, `audit`, `mask`, and `enforce` modes.
- Mask configured sensitive data before provider calls when masking is enabled.
- Reject prompt-injection input before provider calls when enforcement is enabled.
- Mask configured sensitive data in non-streaming provider responses before returning to consumers.
- Block unsafe provider responses when enforcement is enabled.
- Preserve OpenAI-compatible success response shapes.

## Capabilities

### New Capabilities

- `ai-guardrails`: Defines configurable PII masking, prompt input safety, response safety, and guardrail logging.

### Modified Capabilities

- `security-screening`: Upgrades log-only screening behavior to support masking and enforcement modes.

## Impact

- Affects `app/main.py`, `config.yaml`, tests, README, and Kubernetes deployment/configuration docs.
- Keeps Kong OSS as the routing layer and implements guardrails inside this FastAPI/LiteLLM gateway.
- No breaking change for successful OpenAI-compatible chat completion responses.
