# AI Gateway Service

Unified OpenAI-compatible API gateway for OpenAI and DeepSeek, powered by LiteLLM.

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set API keys
export OPENAI_API_KEY=sk-...
export DEEPSEEK_API_KEY=sk-...

# Start server
litellm --config config.yaml --port 4000
```

### Health Check

```bash
curl http://localhost:4000/health        # Returns {"status": "ok"}
curl http://localhost:4000/readiness     # Checks provider connectivity
curl http://localhost:4000/v1/models     # Lists configured models
```

### Docker

```bash
docker build -t ai-gateway-service .
docker run -p 4000:4000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY \
  ai-gateway-service
```

## Deployment (GKE)

1. Configure Artifact Registry:
   ```bash
   gcloud artifacts repositories create ai-gateway-repo \
     --repository-format=docker \
     --location=REGION
   ```

2. Build and push:
   ```bash
   gcloud builds submit --config=cloudbuild.yaml
   ```

3. Apply Kubernetes manifests:
   ```bash
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/secret.yaml    # Update with real keys first
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   ```

4. Verify deployment:
   ```bash
   kubectl -n ai-gateway get pods
   kubectl -n ai-gateway logs -l app=ai-gateway --tail=50
   ```

## Model Routing

| Model Prefix   | Provider  | Endpoint |
|----------------|-----------|----------|
| `gpt-4o*`      | OpenAI    | `POST /v1/chat/completions` |
| `gpt-4o-mini*` | OpenAI    | `POST /v1/chat/completions` |
| `deepseek-*`   | DeepSeek  | `POST /v1/chat/completions` |

## Configuration

All model and provider configuration is in `config.yaml`. No hardcoded API keys — keys are injected via environment variables at runtime.
