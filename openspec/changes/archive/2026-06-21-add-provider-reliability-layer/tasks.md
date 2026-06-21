## 1. Tests

- [x] 1.1 Add retry success test
- [x] 1.2 Add fallback success test
- [x] 1.3 Add circuit open skip test
- [x] 1.4 Add half-open success and failure tests
- [x] 1.5 Add reliability log metadata test
- [x] 1.6 Add compatibility test for existing request shape

## 2. Implementation

- [x] 2.1 Add reliability config to `config.yaml`
- [x] 2.2 Add circuit breaker state helpers
- [x] 2.3 Add retry/timeout provider call helper
- [x] 2.4 Add fallback candidate resolution by model alias
- [x] 2.5 Route streaming and non-streaming provider setup through reliability helper
- [x] 2.6 Add reliability metadata to structured logs

## 3. Documentation And Verification

- [x] 3.1 Update README with reliability behavior, limits, and config
- [x] 3.2 Run full tests and strict OpenSpec validation
- [x] 3.3 Commit Phase 4 separately
