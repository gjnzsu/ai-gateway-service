FROM ghcr.io/berriai/litellm:main

WORKDIR /app

# Copy config
COPY config.yaml /app/config.yaml

# Copy custom routes dir (empty for now, reserved for future)
COPY app/ /app/app/

# Expose port
EXPOSE 4000

# Environment variables injected at runtime via Kubernetes secrets
# LITELLM_MASTER_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY, OTEL_EXPORTER_OTLP_ENDPOINT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:4000/health', timeout=5).raise_for_status()"

# Start LiteLLM server with config
CMD ["--config", "/app/config.yaml", "--port", "4000", "--host", "0.0.0.0"]
