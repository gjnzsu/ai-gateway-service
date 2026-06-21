## 1. Test Harness

- [x] 1.1 Configure tests to import the FastAPI app with a deterministic local config path
- [x] 1.2 Replace live `localhost:4000` requests with in-process ASGI requests

## 2. Gateway Behavior

- [x] 2.1 Add failing tests for readiness success and missing-key behavior
- [x] 2.2 Add failing tests for chat validation, model alias forwarding, and streaming behavior
- [x] 2.3 Implement deterministic config path resolution
- [x] 2.4 Implement readiness checks for required API key environment variables
- [x] 2.5 Fix chat completion pass-through kwargs so `stream` is not duplicated

## 3. Hygiene And Documentation

- [x] 3.1 Add Python cache patterns to `.gitignore`
- [x] 3.2 Clean README encoding and update local dev/readiness/secret guidance
- [x] 3.3 Run the full test suite and OpenSpec validation
