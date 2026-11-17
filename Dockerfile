# ==============================================================================
# Smart AI Real-Time Traffic Monitoring System - Dockerfile
# ==============================================================================

# Base image with Python 3.11 (Debian slim for minimal footprint & stability)
FROM python:3.11-slim

# Labels & Metadata
LABEL maintainer="Smart Traffic AI Engineering Team"
LABEL description="AI-based real-time vehicle detection, tracking, counting and traffic density analysis system."
LABEL version="1.0.0"

# Set environment variables to optimize Python runtime in container
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5000 \
    PYTHONPATH=/app

# Install system runtime dependencies required by OpenCV & network utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside container
WORKDIR /app

# Copy dependency specifications first for Docker layer caching
COPY requirements.txt /app/requirements.txt

# Install lightweight CPU-only PyTorch first (avoids ~3GB NVIDIA CUDA packages)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy project directories and source code
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY models/ /app/models/
COPY uploads/ /app/uploads/
COPY logs/ /app/logs/
COPY .env.example /app/.env.example

# Ensure necessary runtime directories exist
RUN mkdir -p /app/logs /app/uploads /app/backend/database

# Expose server HTTP port
EXPOSE 5000

# Container healthcheck against /api/health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Start Flask Application Server
CMD ["python", "backend/app.py"]
