# SuperDots Dockerfile
# Multi-stage build for optimized container size

# Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash superdots

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --user -r requirements.txt

# Copy source code
COPY . .

# Install SuperDots
RUN pip install --user .

# Runtime stage
FROM python:3.11-slim as runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/superdots/.local/bin:$PATH" \
    SUPERDOTS_CONFIG_DIR="/home/superdots/.superdots"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash superdots

# Copy installed packages from builder stage
COPY --from=builder /home/superdots/.local /home/superdots/.local

# Set working directory
WORKDIR /home/superdots

# Switch to non-root user
USER superdots

# Create SuperDots directories
RUN mkdir -p ~/.superdots ~/.config/superdots

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD superdots --version || exit 1

# Default command
CMD ["superdots", "--help"]

# Labels
LABEL org.opencontainers.image.title="SuperDots" \
    org.opencontainers.image.description="Cross-platform dotfiles and configuration management tool" \
    org.opencontainers.image.version="1.0.0" \
    org.opencontainers.image.authors="SuperDots Team" \
    org.opencontainers.image.url="https://github.com/superdots/superdots" \
    org.opencontainers.image.source="https://github.com/superdots/superdots" \
    org.opencontainers.image.licenses="MIT"
