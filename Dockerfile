FROM python:3.11-slim AS builder

WORKDIR /app

COPY api_server/requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt

FROM node:18-alpine AS frontend-builder

WORKDIR /app

COPY frontend/package*.json ./

RUN npm ci

COPY frontend/ ./

RUN npm run build

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

COPY api_server/ ./api_server/

COPY --from=frontend-builder /app/dist ./frontend/dist

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
