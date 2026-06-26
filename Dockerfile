FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.3 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PATH="/app/.venv/bin:$PATH"
# Raiz que o Chainlit usa para localizar .chainlit/, public/ e chainlit*.md.
ENV CHAINLIT_APP_ROOT=/app

WORKDIR /app

# Camada de dependencias (cacheada enquanto pyproject/uv.lock nao mudarem).
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

# Codigo da aplicacao: agents/, ui/ (server + chat_app + templates/static),
# public/ (tema, logo, favicon, custom.css), .chainlit/ e chainlit*.md.
COPY . .

RUN mkdir -p /app/runtime/database /app/runtime/vector_store/knowledge_markdown
RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8501

# Considera saudavel quando a landing (FastAPI) responde. start-period generoso
# porque o entrypoint roda db init + importar + rag index antes de subir o app.
HEALTHCHECK --interval=30s --timeout=5s --start-period=300s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://localhost:'+os.getenv('PORT','8501')+'/')" || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
