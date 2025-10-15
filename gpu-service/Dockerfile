# Multi-stage build for SIRA GPU Service
FROM python:3.11-slim as builder

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/src" \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8002 \
    WORKERS=1 \
    ENVIRONMENT=production \
    DEBUG=false

# Install runtime dependencies and NVIDIA tools
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Add NVIDIA package repositories (for GPU support)
RUN curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
    && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    tee /etc/apt/sources.list.d/nvidia-container-toolkit.list || true

# Create non-root user for security
RUN groupadd -r sira && useradd -r -g sira -d /app -s /bin/bash sira

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create app directory and set ownership
RUN mkdir -p /app/src /app/logs /app/tmp /app/cache && \
    chown -R sira:sira /app

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=sira:sira src/ ./src/
COPY --chown=sira:sira requirements.txt ./

# Create startup script
COPY --chown=sira:sira <<EOF /app/start.sh
#!/bin/bash
set -e

# Health check function
health_check() {
    curl -f http://localhost:\${PORT:-8002}/health || exit 1
}

# Export health check function
export -f health_check

# Wait for OLLAMA if specified
if [ ! -z "\$OLLAMA_HOST" ]; then
    echo "Waiting for OLLAMA at \$OLLAMA_HOST..."
    timeout 300 bash -c 'until curl -f \$OLLAMA_HOST/api/tags; do sleep 5; done' || {
        echo "OLLAMA not available after 5 minutes, starting anyway..."
    }
fi

# Start the application
exec uvicorn src.main:app \\
    --host 0.0.0.0 \\
    --port \${PORT:-8002} \\
    --workers \${WORKERS:-1} \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --access-log \\
    --log-level info \\
    --timeout-keep-alive 30 \\
    --timeout-graceful-shutdown 30
EOF

RUN chmod +x /app/start.sh

# Switch to non-root user
USER sira

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Default command
CMD ["/app/start.sh"]

# Labels
LABEL maintainer="SIRA Team" \
      version="1.0.0" \
      description="SIRA GPU Service with OLLAMA integration" \
      org.opencontainers.image.title="SIRA GPU Service" \
      org.opencontainers.image.description="GPU inference service for environmental recovery system" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="SIRA Project"
