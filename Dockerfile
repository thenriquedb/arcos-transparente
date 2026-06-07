FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.3 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY . .

RUN uv sync --frozen --no-dev
RUN mkdir -p /app/runtime/database /app/runtime/vector_store/knowledge_markdown
RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8501

ENTRYPOINT ["/app/docker/entrypoint.sh"]
