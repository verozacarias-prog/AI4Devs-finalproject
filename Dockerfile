# One image for every backend process, with the dashboard build inside it (ADR 0021).

# Stage 1: compiles the dashboard to static files. Nothing of Node reaches the final image.
FROM node:26-slim AS dashboard

WORKDIR /srv/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: the backend, which serves that build under /app (ADR 0016).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DASHBOARD_DIR=/srv/dashboard

WORKDIR /srv/backend

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/alembic.ini .
COPY backend/migrations migrations
COPY backend/app app
COPY --from=dashboard /srv/frontend/dist /srv/dashboard

# The image never runs as root.
RUN useradd --system --uid 10001 --no-create-home platita
USER platita

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"]

CMD ["python", "-m", "app.main"]
