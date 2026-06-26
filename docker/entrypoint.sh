#!/bin/sh
set -eu

runtime_database_dir="/app/runtime/database"
runtime_rag_dir="${RAG_PERSIST_DIRECTORY:-/app/runtime/vector_store/knowledge_markdown}"
auto_bootstrap_on_start="${AUTO_BOOTSTRAP_ON_START:-1}"
bootstrap_sentinel="/app/runtime/.bootstrap_done"

mkdir -p "$runtime_database_dir" "$runtime_rag_dir"

# Forca o banco do app para o SQLite do runtime, ignorando um DATABASE_URL
# injetado pela plataforma (ex.: Railway com plugin Postgres sequestra essa env
# e quebraria o app, que e SQLite-only). Override explicito via APP_DATABASE_URL.
export DATABASE_URL="${APP_DATABASE_URL:-sqlite:////app/runtime/database/transparencia.db}"
export RAG_PERSIST_DIRECTORY="$runtime_rag_dir"

if [ "$#" -eq 0 ]; then
  if [ "$auto_bootstrap_on_start" = "1" ]; then
    # Migrations sao idempotentes e baratas: aplicadas sempre.
    echo "[docker-entrypoint] Aplicando migrations..."
    python cli.py db init

    # importar (recria a base) e rag index (embeddings pagos da OpenAI) sao caros.
    # Rodam so uma vez: a sentinela em /app/runtime persiste se houver Volume,
    # evitando re-seed e custo a cada restart/redeploy. Force com FORCE_BOOTSTRAP=1.
    if [ -f "$bootstrap_sentinel" ] && [ "${FORCE_BOOTSTRAP:-0}" != "1" ]; then
      echo "[docker-entrypoint] Bootstrap ja realizado (sentinela presente); pulando importar/rag index."
    else
      echo "[docker-entrypoint] Importando dados publicos..."
      python cli.py importar

      echo "[docker-entrypoint] Gerando indice RAG..."
      python cli.py rag index

      touch "$bootstrap_sentinel"
      echo "[docker-entrypoint] Bootstrap concluido."
    fi
  else
    echo "[docker-entrypoint] Bootstrap automatico desativado por AUTO_BOOTSTRAP_ON_START=0"
  fi

  # --proxy-headers/--forwarded-allow-ips: o Railway termina TLS na borda e fala
  # HTTP com o container; sem isto o uvicorn assume http e gera redirects/cookies
  # inseguros (ex.: 307 /chat -> /chat/ apontando para http://).
  set -- \
    uvicorn ui.server:app \
    --host 0.0.0.0 \
    --port "${PORT:-8501}" \
    --proxy-headers \
    --forwarded-allow-ips="*"
fi

exec "$@"
