# Multi-stage build for SIRA Backend Service
# Optimized for Python 3.11+ and Cloud Run deployment

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/src" \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080 \
    WORKERS=4 \
    ENVIRONMENT=production \
    DEBUG=false

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r sira && useradd -r -g sira -d /app -s /bin/bash sira

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create app directory and set ownership
RUN mkdir -p /app/src /app/logs /app/tmp && \
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
    curl -f http://localhost:\${PORT:-8080}/api/v1/health || exit 1
}

# Export health check function
export -f health_check

# Start the application
exec uvicorn src.main:app \\
    --host 0.0.0.0 \\
    --port \${PORT:-8080} \\
    --workers \${WORKERS:-4} \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --access-log \\
    --log-level info \\
    --timeout-keep-alive 30 \\
    --timeout-graceful-shutdown 30
EOF

# Make startup script executable
RUN chmod +x /app/start.sh

# Switch to non-root user
USER sira

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/api/v1/health || exit 1

# Default command
CMD ["/app/start.sh"]

# Labels for metadata
LABEL maintainer="SIRA Team" \
      version="1.0.0" \
      description="SIRA Backend Service - Sistema Inteligente de Recuperação Ambiental" \
      org.opencontainers.image.title="SIRA Backend" \
      org.opencontainers.image.description="Backend service for intelligent environmental recovery system" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="SIRA Project" \
      org.opencontainers.image.licenses="MIT"
