## 1. Compatibility and pricing preparation

- [x] 1.1 Verify official self-hosted Langfuse topology and resource needs; document tested backend/SDK pins and explicit trace, cost, unknown-cost, and content-capture behavior.
- [x] 1.2 Verify the pilot model against installed LiteLLM and establish a versioned USD price mapping including available cached-token details; update design with evidence.

## 2. Isolated backend

- [x] 2.1 Add an isolated local deployment profile based on the official Langfuse stack, with supporting services, health checks, and untracked credential configuration.
- [x] 2.2 Document startup, project credential setup, shutdown, and successful metadata-only trace ingestion against the pinned stack.

## 3. Gateway telemetry

- [x] 3.1 Add optional pilot enablement, bounded attribution validation, deterministic run trace mapping, and unique call/attempt identities.
- [x] 3.2 Add content-free provider-attempt observations, preserving original usage and actual model before guardrail response processing.
- [x] 3.3 Add the authoritative pricing adapter and explicit unknown-usage/pricing handling, with incomplete accounting indicators.
- [x] 3.4 Add bounded background export and shutdown flush; make initialization/export failures fail-open and diagnostic.

## 4. Companion Market Studio integration

- [x] 4.1 Prepare and implement a separate coordinated change in AI Market Studio: `market-briefing-agent`, fresh run UUID per invocation, immutable per-call header propagation including injected-client paths, and concurrency isolation.
- [x] 4.2 Ensure pilot attribution reaches Kong and the shared gateway, with no direct-provider bypass in the selected market-briefing workflow; retain existing SRE/business metrics.

## 5. Verification and acceptance

- [x] 5.1 Add meaningful mocked tests for concurrent attribution, reused request IDs, retries/fallbacks, missing usage/pricing, cached usage, and post-provider guardrail rejection.
- [x] 5.2 Verify telemetry payloads omit content/secrets, outages preserve responses, queues are bounded, and disabled/streaming/embedding paths retain existing behavior.
- [x] 5.3 Run gateway and companion repository lint/tests and validate deployment configuration; record commands and results.
- [ ] 5.4 Execute a bounded real-provider pilot for two repeated and overlapping market-briefing runs; inspect Langfuse and reconcile unique call counts, known-cost totals, and missing-data indicators. Synthetic live ingestion is complete, but the billable provider-backed acceptance run remains.
- [x] 5.5 Document evidence, price/version configuration, observed limitations, and disablement rollback; update architecture documentation if implementation alters documented flows.

Validation: gateway 86 tests passed; focused FinOps 12 tests passed; minimal Ruff error checks passed; Compose configuration validated with generated ignored credentials. Market Studio lint passed and 265 tests passed with 1 existing skip. Langfuse SDK 4.17.0 exported two overlapping run identities into the live self-hosted v4.50.0 stack. Each trace contained two content-free generations: one explicit known cost and one unknown cost with model/cost fields omitted. The v4.50.0 expanded observation API returned 502, so the bounded smoke script verified the same persisted fields through its local ClickHouse fallback. This smoke used synthetic gateway attempt records and did not call a billable model provider.
