# Docker

## Status

O repositório agora inclui suporte oficial a Docker com:

- `Dockerfile` para build da imagem
- `compose.yaml` para o fluxo local canônico
- `docker/entrypoint.sh` para preparar o runtime stateful e subir o web app por padrão

## Objetivo

Padronizar a execucao do projeto em um container unico e stateful, preservando:

- interface web em Streamlit
- banco SQLite local
- indice vetorial local do RAG
- comandos operacionais ja existentes em `cli.py`

## Fluxo Oficial

O fluxo Docker oficial usa uma imagem unica do projeto e `docker compose` como
orquestracao principal.

Sequencia recomendada:

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

No Docker, o `compose.yaml` injeta defaults seguros para o runtime stateful sem
exigir que voce troque o `DATABASE_URL` local do seu `.env`:

```env
DOCKER_PORT=8501
DOCKER_DATABASE_URL=sqlite:////app/runtime/database/transparencia.db
DOCKER_RAG_PERSIST_DIRECTORY=/app/runtime/vector_store/knowledge_markdown
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

## Referencias

- [Proposal da change](../openspec/changes/containerize-with-docker/proposal.md)
- [Design da change](../openspec/changes/containerize-with-docker/design.md)
- [Spec `dockerized-runtime`](../openspec/changes/containerize-with-docker/specs/dockerized-runtime/spec.md)
