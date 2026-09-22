# RAG embedding contract

`POST /v1/embeddings` accepts `model`, `input`, `encoding_format`, `dimensions`
and `user`. Input is nonempty text or a nonempty batch of nonempty text strings.
Only aliases configured in `embedding_models` are accepted. Client-supplied
provider URLs, credentials and arbitrary LiteLLM parameters are rejected.

The initial alias maps `text-embedding-3-small` to `openai/text-embedding-3-small`.
The provider key comes from Gateway's `OPENAI_API_KEY`. Float/base64 output,
response indexes and token usage are preserved. The timeout uses Gateway's
existing provider timeout. There is no cross-model fallback or text masking:
embedding semantics must match RAG's existing index. Provider errors are sanitized;
rate limits return 429, timeouts 504, invalid provider requests 400 and other failures 502.

Embedding audit events contain request ID, model, consumer, policy decision,
usage, duration and error class; never input text or vectors. Existing observability
ingestion receives token counts and caller attribution. Consumer-model policy remains
log-only, as on the existing chat path. Kong owns configured ingress rate limits.

Set `AI_GATEWAY_SERVICE_TOKEN` to enable bearer-token checks on every `/v1/*` route.
Coordinate this with existing applications; unset preserves existing deployment
behavior. This is a shared POC service token, not per-consumer identity verification.
RAG config uses `AI_GATEWAY_BASE_URL` and `AI_GATEWAY_API_KEY`; it must not retain
provider keys. Provider calls remain mock-only in the local tests. Actual model
compatibility, Kong traversal and cluster egress restrictions require rollout checks.
