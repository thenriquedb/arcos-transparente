# Docker

## Status

O repositório agora inclui suporte oficial a Docker com:

- `Dockerfile` para build da imagem
- `compose.yaml` para o fluxo local canônico
- `docker/entrypoint.sh` para preparar o runtime stateful, executar bootstrap automático e subir o web app por padrão

## Objetivo

Padronizar a execucao do projeto em um container unico e stateful, preservando:

- interface web em FastAPI (landing) + Chainlit (chat)
- banco SQLite local
- indice vetorial local do RAG
- comandos operacionais ja existentes em `cli.py`

## Startup Automatico

No startup padrão do container, o entrypoint agora executa automaticamente:

```bash
python cli.py db init
python cli.py importar
python cli.py rag index
```

So depois disso o app FastAPI/Chainlit sobe (uvicorn). Isso permite que deploys em
plataformas como Railway inicializem o banco e o índice RAG sem precisar abrir
console manual.

Se voce quiser desativar esse comportamento em ambiente local ou em algum deploy
específico:

```env
AUTO_BOOTSTRAP_ON_START=0
```

## Fluxo Oficial

O fluxo Docker oficial usa uma imagem unica do projeto e `docker compose` como
orquestracao principal.

Para deploy automatizado, o caminho mais simples passa a ser:

```bash
docker compose build
docker compose up app
```

Se voce quiser rodar as rotinas manualmente, o fluxo continua disponivel:

```bash
docker compose build
docker compose run --rm app python cli.py db init
docker compose run --rm app python cli.py importar
docker compose run --rm app python cli.py rag index
docker compose up app
```

O mesmo fluxo tambem devera permitir rodar verificacoes como:

```bash
docker compose run --rm app python cli.py db status
docker compose run --rm app python cli.py rag status
```

## Variaveis De Ambiente

O fluxo continua usando o contrato atual do projeto para o chatbot:

```env
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=sua_chave_openai_aqui
```

Observabilidade continua opt-in dentro do mesmo fluxo:

```env
OBSERVABILITY_ENABLED=true
OBSERVABILITY_PROVIDER=langsmith
LANGSMITH_API_KEY=sua_chave_langsmith
LANGSMITH_PROJECT=arcos-transparente
# LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

Se essas variaveis nao forem definidas, o runtime usa o provider `noop` e nao
envia spans para fora do container.

No Docker, o `compose.yaml` injeta defaults seguros para o runtime stateful sem
exigir que voce troque o `DATABASE_URL` local do seu `.env`:

```env
DOCKER_PORT=8501
DOCKER_DATABASE_URL=sqlite:////app/runtime/database/transparencia.db
DOCKER_RAG_PERSIST_DIRECTORY=/app/runtime/vector_store/knowledge_markdown
AUTO_BOOTSTRAP_ON_START=1
```

Se esses overrides nao forem definidos, o `compose.yaml` usa exatamente esses
valores como padrao.

## Persistencia

O diretório `/app/runtime` devera ficar em um volume persistente para preservar:

- banco SQLite e arquivos `-wal` e `-shm`
- artefatos persistidos do Chroma

Sem esse volume, a aplicacao perdera o banco importado e o indice RAG a cada
recriacao do container.

## Limites Operacionais

- A implementacao atual e de instancia unica stateful.
- O fluxo nao pressupoe multiplas replicas concorrendo sobre o mesmo volume.
- A importacao continua recriando a base inteira antes da carga.
- Com `AUTO_BOOTSTRAP_ON_START=1`, esse recarregamento acontece a cada subida do container.

## Referencias

- [Proposal da change](../openspec/changes/containerize-with-docker/proposal.md)
- [Design da change](../openspec/changes/containerize-with-docker/design.md)
- [Spec `dockerized-runtime`](../openspec/changes/containerize-with-docker/specs/dockerized-runtime/spec.md)
