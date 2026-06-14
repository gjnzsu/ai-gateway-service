## ADDED Requirements

### Requirement: Provider calls are bounded by timeout
The gateway SHALL apply a configured timeout to provider calls.

#### Scenario: Provider call exceeds timeout
- **WHEN** a provider call exceeds the configured timeout
- **THEN** the attempt fails and reliability handling proceeds to retry or fallback

### Requirement: Provider calls are retried with bounded attempts
The gateway SHALL retry failed provider calls up to the configured maximum attempts.

#### Scenario: Retry succeeds
- **WHEN** the first provider attempt fails and a later retry succeeds
- **THEN** the gateway returns the successful provider response

### Requirement: Fallback model aliases are tried after primary failure
The gateway SHALL try configured fallback model aliases when the primary model fails or its circuit is open.

#### Scenario: Primary fails and fallback succeeds
- **WHEN** the primary model fails after configured attempts
- **THEN** the gateway tries the configured fallback model and returns the fallback response if it succeeds

### Requirement: Circuit breaker opens after repeated failures
The gateway SHALL open a circuit for a resolved provider model after the configured failure threshold.

#### Scenario: Circuit opens
- **WHEN** a resolved provider model reaches the failure threshold
- **THEN** future requests skip that model until cooldown expires

### Requirement: Circuit breaker transitions half-open after cooldown
The gateway SHALL allow a passive probe request after an open circuit's cooldown expires.

#### Scenario: Half-open probe succeeds
- **WHEN** the cooldown expires and the probe succeeds
- **THEN** the gateway closes the circuit

#### Scenario: Half-open probe fails
- **WHEN** the cooldown expires and the probe fails
- **THEN** the gateway opens the circuit again

### Requirement: Reliability behavior is observable
The gateway SHALL include reliability metadata in structured chat completion logs.

#### Scenario: Fallback response is logged
- **WHEN** a fallback model is used
- **THEN** the structured log includes selected resolved model, fallback source, attempt count, and circuit state

### Requirement: Existing consumers remain compatible
The gateway SHALL preserve existing OpenAI-compatible request and response behavior.

#### Scenario: Existing request still works
- **WHEN** `ai-market-studio` sends an existing chat completion request
- **THEN** the gateway returns a compatible provider response
