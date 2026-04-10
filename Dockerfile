FROM python:3.11-slim

WORKDIR /app

# Install LiteLLM and dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ /app/app/
COPY config.yaml /app/config.yaml

# Expose port
EXPOSE 4000

# Environment variables injected at runtime via Kubernetes secrets
# OPENAI_API_KEY, DEEPSEEK_API_KEY

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:4000/health', timeout=5).raise_for_status()"

# Run the custom LiteLLM proxy server
CMD ["python", "-m", "app.main"]
