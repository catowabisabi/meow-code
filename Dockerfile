# syntax=docker/dockerfile:1
# ============================================================
# Cato Claude - Full Stack Docker Image
# ============================================================
# Build: docker build -t cato-claude .
# Run:   docker run -p 7778:7778 -p 3000:3000 cato-claude
# Dev:   docker run -p 7778:7778 -p 3000:3000 -v $(pwd):/app cato-claude python main.py
# ============================================================

# ── Stage 1: Base OS ──────────────────────────────────────────
FROM python:3.11-slim AS base

# Install system dependencies FIRST (layer caching)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ── Stage 2: Node.js ──────────────────────────────────────────
FROM base AS node-builder

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g pnpm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/webui

# Copy package files first for caching
COPY webui/client/package.json webui/client/pnpm-lock.yaml* ./

# Install dependencies
RUN npm install --legacy-peer-deps \
    || pnpm install --legacy-peer-deps \
    || npm install

# Copy source and build
COPY webui/client/src ./src
COPY webui/client/index.html ./
COPY webui/client/tsconfig.json ./
COPY webui/client/vite.config.ts ./
COPY webui/client/public ./public || true

RUN npm run build || echo "Build may require additional config"

# ── Stage 3: Python dependencies ───────────────────────────────
FROM node-builder AS python-deps

WORKDIR /app/api_server

COPY api_server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 4: Production image ───────────────────────────────────
FROM python:3.11-slim AS prod

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements
COPY api_server/requirements.txt ./api_server/

# Install Python dependencies
RUN pip install --no-cache-dir -r api_server/requirements.txt

# Copy API server source
COPY api_server/ ./api_server/

# Copy pre-built webui dist (if exists)
COPY webui/ ./webui/

# Copy root config
COPY config.py ./

# Environment defaults
ENV PYTHONPATH=/app
ENV CATO_HOST=0.0.0.0
ENV CATO_PORT=7778

EXPOSE 7778

# Default startup
CMD ["python", "-m", "uvicorn", "api_server.main:app", "--host", "0.0.0.0", "--port", "7778", "--reload"]

# ── Stage 5: Development image ─────────────────────────────────
FROM base AS dev

RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    git \
    curl \
    procps \
    vim \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dev deps
COPY api_server/requirements.txt ./api_server/
RUN pip install --no-cache-dir -r api_server/requirements.txt \
    && pip install --no-cache-dir ipython jupyter

# Install Node dev deps
COPY webui/client/package.json ./webui/client/
RUN cd webui/client && npm install

# Copy all source
COPY . .

ENV PYTHONPATH=/app
ENV CATO_HOST=0.0.0.0
ENV CATO_PORT=7778

EXPOSE 7778 3000

# Dev startup - enables hot reload
CMD ["python", "-m", "uvicorn", "api_server.main:app", "--host", "0.0.0.0", "--port", "7778", "--reload"]
