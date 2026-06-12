## 1. Tests

- [x] 1.1 Add tests for allowed model policy log fields
- [x] 1.2 Add tests for disallowed model policy log fields while request still succeeds
- [x] 1.3 Add tests for missing consumer header using default policy
- [x] 1.4 Add compatibility test for `ai-market-studio`

## 2. Implementation

- [x] 2.1 Add `consumer_policies` to `config.yaml`
- [x] 2.2 Add policy loading and default lookup helpers
- [x] 2.3 Add policy evaluation helper
- [x] 2.4 Include policy fields in structured chat completion logs
- [x] 2.5 Keep policy evaluation log-only with no request blocking

## 3. Documentation And Verification

- [x] 3.1 Update README with log-only consumer model policy behavior
- [x] 3.2 Run full tests and strict OpenSpec validation
- [x] 3.3 Commit Phase 3 separately
