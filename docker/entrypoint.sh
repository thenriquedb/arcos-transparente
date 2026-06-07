#!/bin/sh
set -eu

runtime_database_dir="/app/runtime/database"
runtime_rag_dir="${RAG_PERSIST_DIRECTORY:-/app/runtime/vector_store/knowledge_markdown}"

mkdir -p "$runtime_database_dir" "$runtime_rag_dir"

export DATABASE_URL="${DATABASE_URL:-sqlite:////app/runtime/database/transparencia.db}"
export RAG_PERSIST_DIRECTORY="$runtime_rag_dir"

if [ "$#" -eq 0 ]; then
  set -- \
    streamlit run agents/chatbot/web.py \
    --server.address=0.0.0.0 \
    --server.port="${PORT:-8501}"
fi

exec "$@"
