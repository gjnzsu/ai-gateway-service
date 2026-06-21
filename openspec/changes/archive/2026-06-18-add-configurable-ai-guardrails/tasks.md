## 1. Tests

- [x] 1.1 Add request-side PII masking test.
- [x] 1.2 Add prompt safety enforcement test.
- [x] 1.3 Add response-side PII masking test.
- [x] 1.4 Add response safety blocking test.

## 2. Implementation

- [x] 2.1 Implement guardrail mode helpers and safe error bodies.
- [x] 2.2 Implement request message masking before provider calls.
- [x] 2.3 Implement prompt safety blocking before provider calls.
- [x] 2.4 Implement non-streaming response masking and blocking.
- [x] 2.5 Add safe guardrail action metadata to structured logs.

## 3. Documentation and Validation

- [x] 3.1 Update `config.yaml` with guardrail defaults while preserving existing model changes.
- [x] 3.2 Update README with guardrail modes and limitations.
- [x] 3.3 Run OpenSpec validation.
- [x] 3.4 Run targeted security screening tests.
- [x] 3.5 Run full test suite.
