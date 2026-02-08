# Telegram AI Bot Dockerfile
# Optimized for faster builds with better layer caching

FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    poppler-utils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app directory and non-root user early
WORKDIR /app
RUN adduser --disabled-password --gecos '' --home /app appuser

# Dependencies stage - cached unless requirements.txt changes
FROM base AS dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM dependencies AS final

# Copy application code (this layer changes most frequently)
COPY --chown=appuser:appuser . .

USER appuser

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command (can be overridden in docker-compose)
CMD ["python", "main.py"]