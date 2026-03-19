# =============================================================
# backend/Dockerfile
# PURPOSE:  Containerizes the FastAPI backend
#
# PORTABLE TO:
#   Railway, AWS ECS, Azure Container Apps,
#   GCP Cloud Run, DigitalOcean App Platform, any VPS
#
# BUILD:    docker build -t artha-backend .
# RUN:      docker run -p 8000:8000 --env-file .env artha-backend
#
# LAYERS (ordered for best cache performance):
#   1. Base Python image
#   2. System dependencies (rarely changes)
#   3. Python dependencies (changes occasionally)
#   4. App code (changes most often)
#   Layers 1-3 are cached — only layer 4 rebuilds on code change
#
# SIZE TARGET: Keep under 500MB
#   Current: ~280MB with slim base
#
# LAST UPDATED: March 2026
# =============================================================

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# System dependencies
# curl: needed for healthcheck
# gcc: needed to compile some Python packages
# RUN in one layer to keep image small
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*
# NOTE: rm -rf /var/lib/apt/lists/* removes apt cache
# This alone saves ~40MB from the image

# Copy requirements first (before code)
# WHY: If only code changes (not requirements), Docker
# uses the cached pip install layer — much faster builds
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
# --no-cache-dir saves ~50MB by not storing pip cache

# Copy application code
# This layer rebuilds on every code change
COPY . .

# Create non-root user for security
# Running as root in containers is a security risk
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Expose port
EXPOSE 8000

# Health check — used by Docker, Railway, AWS, Azure
# If this fails 3 times, container is marked unhealthy
# and restarted automatically
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
# --host 0.0.0.0: listen on all interfaces (required in Docker)
# --port 8000: explicit port
# --workers 1: single worker for free tier (512MB RAM)
# UPGRADE: --workers 4 when on paid plan with 2GB+ RAM
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
