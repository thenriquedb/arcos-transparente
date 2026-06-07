#!/bin/sh
set -eu

runtime_database_dir="/app/runtime/database"
runtime_rag_dir="${RAG_PERSIST_DIRECTORY:-/app/runtime/vector_store/knowledge_markdown}"
auto_bootstrap_on_start="${AUTO_BOOTSTRAP_ON_START:-1}"

mkdir -p "$runtime_database_dir" "$runtime_rag_dir"

export DATABASE_URL="${DATABASE_URL:-sqlite:////app/runtime/database/transparencia.db}"
export RAG_PERSIST_DIRECTORY="$runtime_rag_dir"

if [ "$#" -eq 0 ]; then
  if [ "$auto_bootstrap_on_start" = "1" ]; then
    echo "[docker-entrypoint] Aplicando migrations..."
    python cli.py db init

    echo "[docker-entrypoint] Importando dados publicos..."
    python cli.py importar

    echo "[docker-entrypoint] Gerando indice RAG..."
    python cli.py rag index
  else
    echo "[docker-entrypoint] Bootstrap automatico desativado por AUTO_BOOTSTRAP_ON_START=0"
  fi

  set -- \
    streamlit run agents/chatbot/web.py \
    --server.address=0.0.0.0 \
    --server.port="${PORT:-8501}"
fi

exec "$@"
