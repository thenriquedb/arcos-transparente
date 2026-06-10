# Configuração

Todas as variáveis são lidas de um arquivo `.env` na raiz do projeto. O arquivo `.env.example` documenta o contrato canônico usado no bootstrap.

## Variáveis Obrigatórias

| Variável | Obrigatória | Padrão | Descrição |
|----------|------------|--------|-----------|
| `DATABASE_URL` | Sim | — | URL de conexão SQLAlchemy. Ex: `sqlite:///database/transparencia.db` |
| `OPENAI_API_KEY` | Sim (chatbot) | — | Chave de API da OpenAI. Obrigatória para criar o agente. |
| `LLM_PROVIDER` | Sim (chatbot) | — | Provider do LLM. Deve ser `openai` nesta fase. |
| `OPENAI_MODEL` | Sim (chatbot) | — | Modelo OpenAI a usar. Recomendado: `gpt-4.1-mini`. |

## Observabilidade (Opcional)

A observabilidade está desabilitada por padrão. O runtime usa o provider `noop` enquanto `OBSERVABILITY_ENABLED` estiver ausente ou `false`.

| Variável | Obrigatória | Padrão | Descrição |
|----------|------------|--------|-----------|
| `OBSERVABILITY_ENABLED` | Não | `false` | Define se o runtime emite spans de execução. Valores: `true` / `false`. |
| `OBSERVABILITY_PROVIDER` | Não | `noop` | Provider de observabilidade. Valores suportados: `noop`, `langsmith`. |
| `LANGSMITH_API_KEY` | Condicional | — | Obrigatório quando `OBSERVABILITY_PROVIDER=langsmith`. |
| `LANGSMITH_PROJECT` | Condicional | — | Nome do projeto no LangSmith. Obrigatório quando `OBSERVABILITY_PROVIDER=langsmith`. |
| `LANGSMITH_ENDPOINT` | Não | `https://api.smith.langchain.com` | Endpoint da API LangSmith. Opcional. |

## Overrides de Docker

Estas variáveis são injetadas pelo `compose.yaml` e permitem sobrescrever os defaults do runtime local sem alterar o `.env` principal.

| Variável | Obrigatória | Padrão | Descrição |
|----------|------------|--------|-----------|
| `DOCKER_PORT` | Não | `8501` | Porta do Streamlit dentro do container. |
| `DOCKER_DATABASE_URL` | Não | `sqlite:////app/runtime/database/transparencia.db` | URL do banco dentro do container. |
| `DOCKER_RAG_PERSIST_DIRECTORY` | Não | `/app/runtime/vector_store/knowledge_markdown` | Diretório de persistência do Chroma dentro do container. |
| `AUTO_BOOTSTRAP_ON_START` | Não | `1` | Se `1`, executa `db init`, `importar` e `rag index` no startup do container. Use `0` para desabilitar. |

## Exemplo de `.env` Completo

```env
# Banco de dados local
DATABASE_URL=sqlite:///database/transparencia.db

# Chatbot — OpenAI é o único provider suportado nesta fase
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=sk-...

# Observabilidade (opcional)
# OBSERVABILITY_ENABLED=true
# OBSERVABILITY_PROVIDER=langsmith
# LANGSMITH_API_KEY=ls__...
# LANGSMITH_PROJECT=arcos-transparente
# LANGSMITH_ENDPOINT=https://api.smith.langchain.com

# Overrides Docker (opcional — compose.yaml injeta esses valores por padrão)
# DOCKER_PORT=8501
# DOCKER_DATABASE_URL=sqlite:////app/runtime/database/transparencia.db
# DOCKER_RAG_PERSIST_DIRECTORY=/app/runtime/vector_store/knowledge_markdown
# AUTO_BOOTSTRAP_ON_START=1
```
