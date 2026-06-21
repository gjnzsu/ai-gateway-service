# Design

## Scope

Phase 5 adds a local, deterministic security screening layer for `/v1/chat/completions`. The layer evaluates message content before provider calls and emits structured log metadata.

## Configuration

`config.yaml` adds:

```yaml
security_checks:
  mode: log_only
  prompt_injection_patterns:
    - ignore previous instructions
    - reveal system prompt
  sensitive_data_patterns:
    - "(?i)api[_ -]?key\\s*[:=]\\s*[^\\s]+"
```

Pattern matching is case-insensitive for prompt-injection phrases and regular-expression based for sensitive-data patterns.

## Decision Shape

The gateway logs a compact decision:

```json
{
  "security_mode": "log_only",
  "security_allowed": true,
  "security_reason": "security_signal_detected",
  "security_flags": ["prompt_injection", "sensitive_data"]
}
```

`security_allowed` remains `true` in this phase because the feature is visibility-only.

## Compatibility

The screening layer must not:

- require new headers
- change request bodies
- block provider calls
- log full prompt text
- affect streaming and non-streaming response shape

## Risks

- Simple pattern matching can produce false positives and false negatives.
- Regex patterns can be expensive if operators add unsafe expressions.
- Logging a signal without enforcement can create a false sense of protection.

Mitigation: document the feature as log-only and keep default patterns conservative.
