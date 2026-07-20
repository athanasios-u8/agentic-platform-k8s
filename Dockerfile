FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_HTTP_TIMEOUT=120 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache

COPY src ./src
COPY scripts ./scripts
COPY data ./data
COPY docker/entrypoint.sh ./docker/entrypoint.sh

RUN uv sync --frozen --no-dev --no-cache \
    && groupadd --system bookstore \
    && useradd --system --gid bookstore --home-dir /app --shell /usr/sbin/nologin bookstore \
    && chown -R bookstore:bookstore /app

ARG BOOKSTORE_SERVICE_MODULE=bookstore_agents.frontend_gateway.server
ENV BOOKSTORE_SERVICE_MODULE=${BOOKSTORE_SERVICE_MODULE}

USER bookstore

EXPOSE 8101 8102 8103 8104 8201 8202 8203 8204 8205 8206 8207 8300

ENTRYPOINT ["/bin/sh", "/app/docker/entrypoint.sh"]
CMD []
