# Munshi: one container. Vite builds the web UI; FastAPI serves it and the API on one origin (port 8000).
# Single uvicorn process on purpose: live-update subscribers (app/events.py) live in process memory.

# ---- web build -------------------------------------------------------------------------------------
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# ---- python runtime --------------------------------------------------------------------------------
FROM python:3.12-slim AS app
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH"
WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY alembic.ini ./
COPY migrations/ migrations/
COPY app/ app/
COPY seed/ seed/
COPY --from=web /web/dist web/dist
RUN useradd --system --uid 10001 munshi && mkdir -p /srv/.uploads && chown munshi /srv/.uploads
USER munshi
EXPOSE 8000
# Behind CloudFront -> ALB: trust forwarded headers from the load balancer (the ALB is only reachable from CloudFront).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--timeout-keep-alive", "75"]
