# Arcos Transparente

Chatbot cidadão que responde perguntas em linguagem natural sobre dados públicos do município de Arcos (MG).

![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![License](https://img.shields.io/badge/license-AGPL--3.0-green)

## O que faz

Importa XMLs e CSVs do portal da transparência municipal para um banco SQLite normalizado. Um agente LangChain com tools SQL e recuperação semântica (RAG) sobre um acervo markdown curado responde perguntas sobre servidores, contratos, licitações, despesas, receitas, frota, patrimônio, planejamento e mais. A interface padrão é um app FastAPI que serve a landing institucional em `/` e o chat (Chainlit) em `/chat`.

## Instalação Rápida

```bash
git clone https://github.com/thenriquedb/arcos-transparente.git
cd arcos-transparente
cp .env.example .env          # preencha OPENAI_API_KEY
uv sync
uv run python cli.py db init && uv run python cli.py importar && uv run python cli.py rag index
uv run uvicorn ui.server:app --port 8501   # landing em / e chat em /chat
```

Ou via Docker:

```bash
docker compose build && docker compose up app
```

## Documentação

| Documento | Descrição |
|-----------|-----------|
| [Como Funciona](docs/architecture.md) | Arquitetura completa, fluxos e diagramas |
| [Primeiros Passos](docs/getting-started.md) | Instalação, ingestão e execução do chatbot |
| [Configuração](docs/configuration.md) | Todas as variáveis de ambiente |
| [Contribuindo](docs/contributing.md) | Testes, convenções de branch e estilo de código |
| [Tech Stack](docs/tech-stack.md) | Tecnologias e dependências principais |
| [Modelagem do Banco](docs/database.md) | Tabelas, relacionamentos e decisões de schema |
| [Fluxo de Importação](docs/importacao.md) | Pipeline de ingestão e como adicionar novos tipos |
| [Docker](docs/docker.md) | Containerização e deploy |
| [Prompt do Agente](docs/agent-system-prompt.md) | System prompt em produção |

## Dados Cobertos

Contratos · Licitações · Planejamento orçamentário · Despesas · Estoques · Patrimônios · Quadro de pessoal · Folha de pagamento · Servidores · Receitas · Frotas · Transferências financeiras · Eleitos

## Licença

[AGPL-3.0](LICENSE)
