# RAG Worker Service Dockerfile
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files (rag_worker-specific)
COPY rag_worker/pyproject.toml ./pyproject.toml

# Create requirements.txt from pyproject.toml and install dependencies
RUN uv pip compile pyproject.toml --extra-index-url https://download.pytorch.org/whl/cu121 -o requirements.txt

# Production stage
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Install runtime dependencies (git for cloning repositories)
RUN apt-get update && apt-get install -y \
    git \
    python3.11 \
    python3.11-venv \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3.11 /usr/bin/python

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy requirements.txt
COPY --from=builder /app/requirements.txt ./requirements.txt
# Create new Virtual environment and install library
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    python -m venv .venv && \
    /root/.local/bin/uv pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu121 --python .venv/bin/python && \
    chown -R app:app /app

# Copy only rag_worker-related files
COPY --chown=app:app rag_worker/ ./rag_worker/

# Create logs directory with proper permissions
RUN mkdir -p /app/logs && chown -R app:app /app/logs

# Switch to app user
USER app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Health check for Celery worker
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import celery; from rag_worker.celery_app import app; print('Worker running') if app.control.inspect().active() else exit(1)" || exit 1

# Run RAG worker service with 2 concurrent workers
CMD ["/app/.venv/bin/python", "-m", "celery", "-A", "rag_worker.celery_app", "worker", "--loglevel=info", "--concurrency=2"]