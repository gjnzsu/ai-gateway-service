# Agent FinOps Langfuse POC

This experiment measures estimated LLM spend for AI Market Studio market-briefing agent runs. It keeps the inference path unchanged:

```text
AI Market Studio -> Kong -> AI Gateway -> LiteLLM SDK -> provider
                                  |
                                  +-> metadata-only telemetry -> self-hosted Langfuse
```

The first stage covers non-streaming chat completions only. It excludes embeddings, streaming, tool and infrastructure cost, budgets, invoice reconciliation, and complete agent lifecycle status.

## Identity contract

AI Market Studio sends a stable `X-AI-Agent-ID: market-briefing-agent` and a new UUID in `X-AI-Run-ID` for each workflow invocation. `X-Request-ID` continues to correlate the application request. The gateway creates a distinct call ID per HTTP completion and an attempt ID per provider retry or fallback.

## Start the local backend

Docker Desktop's Linux engine must be running. Generate local credentials once:

```powershell
.\scripts\New-FinOpsEnv.ps1
docker compose --env-file .env.finops -f docker-compose.langfuse.yml config --quiet
docker compose --env-file .env.finops -f docker-compose.langfuse.yml up -d
curl.exe "http://localhost:3300/api/public/health?failIfDatabaseUnavailable=true"
```

The UI is available only on `http://localhost:3300`; storage services have no host ports. The official Langfuse v4 topology uses PostgreSQL, ClickHouse, Redis, and S3-compatible MinIO. The verified web, worker, PostgreSQL, ClickHouse, Redis, and MinIO images are pinned by digest. The v4.51.0 release existed in source, but the published web image lagged the worker image during verification, so the POC deliberately uses the matching v4.50.0 web/worker pair that was available.

The generated `.env.finops` is ignored. Headless initialization creates the local organization, project, API keys, and administrator. Changing seed values does not rotate already-persisted credentials.

## Configure the gateway

Copy the generated public and secret key values into the gateway process environment and enable only the pilot:

```powershell
$env:AGENT_FINOPS_ENABLED = "true"
$env:LANGFUSE_BASE_URL = "http://localhost:3300"
$env:LANGFUSE_PUBLIC_KEY = "pk-lf-..."
$env:LANGFUSE_SECRET_KEY = "sk-lf-..."
```

Telemetry is fail-open and uses a bounded background queue. Export initialization, serialization, queue saturation, backend errors, and bounded shutdown timeouts emit content-free diagnostic event names while preserving inference responses. Disable the feature by removing `AGENT_FINOPS_ENABLED` or setting it to `false`.

## Cost behavior

The gateway is the cost calculation authority. The versioned mapping is in `app/finops_prices.json`. It records the actual selected provider model, provider-reported token usage, explicit USD input/output/total cost, and pricing source/version. For `gpt-5.4`, standard per-million rates are $2.50 input, $0.25 cached input, and $15 output; requests above 272K input tokens use the documented multipliers.

Missing or malformed usage and unsupported pricing are `unknown`, never zero. Unknown records omit Langfuse's model and cost fields to prevent automatic pricing, while retaining the actual model in metadata. Timeouts can still incur provider charges without returning usage, so totals are estimated observed spend rather than invoice totals.

Prompts, responses, credentials, and provider error messages are never supplied to Langfuse. Only a sanitized error class is exported. Provider timestamps and duration are stored in metadata; the observation timestamp reflects asynchronous export time.

## Validate a pilot run

Run two sequential market-briefing workflows and then two overlapping workflows. Capture the deterministic Langfuse trace ID from gateway test evidence or calculate it using the same application/agent/run identity. Query each completed trace with a bounded check:

```powershell
$env:LANGFUSE_BASE_URL = "http://localhost:3300"
$env:LANGFUSE_PUBLIC_KEY = "pk-lf-..."
$env:LANGFUSE_SECRET_KEY = "sk-lf-..."
python .\scripts\smoke-langfuse-finops.py <trace-id> --expected-generations <attempt-count>
```

Verify that each run has its own trace, every retry/fallback is a unique generation, known totals match the versioned calculation, unknown records have no model/cost field, and input/output content is absent.

The verified v4.50.0 backend returns HTTP 502 when the public observation API requests expanded fields. The smoke script therefore falls back to the isolated stack's ClickHouse container and checks only aggregate content/cost invariants; it never prints prompt, response, metadata values, or credentials. The live POC sent two overlapping synthetic run identities through the exact gateway exporter. Each trace persisted two content-free generations, with one explicit known cost and one unknown cost that omitted model and cost fields. This validates the telemetry path without making a billable provider call; a controlled real market-briefing invocation remains the rollout gate for provider-response compatibility.

Stop the stack without deleting its data:

```powershell
docker compose --env-file .env.finops -f docker-compose.langfuse.yml down
```

The stack was started and health-checked locally at version 4.50.0, and metadata-only ingestion was verified. Do not use `down --volumes` unless deleting all POC data is intentional.
