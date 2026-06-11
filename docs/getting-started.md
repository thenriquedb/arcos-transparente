# Primeiros Passos

## Pré-requisitos

- **Python 3.13+**
- **uv** — gerenciador de pacotes e ambiente virtual
- **OPENAI_API_KEY** — chave de API da OpenAI (obrigatória para o chatbot)
- Git

Para instalar o `uv`:

```bash
# via script oficial
curl -LsSf https://astral.sh/uv/install.sh | sh

# ou via Homebrew
brew install uv
```

---

## Instalação Local

### 1. Clonar o repositório

```bash
git clone https://github.com/thenriquedb/arcos-transparente.git
cd arcos-transparente
```

### 2. Instalar dependências

```bash
uv sync
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite `.env` e preencha pelo menos:

```env
DATABASE_URL=sqlite:///database/transparencia.db
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=sua_chave_openai_aqui
```

Para a referência completa de variáveis, consulte [docs/configuration.md](./configuration.md).

### 4. Inicializar o banco de dados

```bash
uv run python cli.py db init
```

Este comando cria o banco SQLite e aplica todas as migrations Alembic.

### 5. Importar os dados

```bash
uv run python cli.py importar
```

Para importar apenas um tipo de dado:

```bash
uv run python cli.py importar --tipo contratos
uv run python cli.py importar --tipo licitacoes
uv run python cli.py importar --tipo servidores
uv run python cli.py importar --tipo despesas
uv run python cli.py importar --tipo receitas
uv run python cli.py importar --tipo planejamentos
uv run python cli.py importar --tipo patrimonios
uv run python cli.py importar --tipo quadro_pessoal
uv run python cli.py importar --tipo transferencias_financeiras
uv run python cli.py importar --tipo estoques
uv run python cli.py importar --tipo frotas
uv run python cli.py importar --tipo folha_pagamento
```

Para filtrar por ano:

```bash
uv run python cli.py importar --tipo receitas --ano 2025
```

Para forçar recarga limpando dados existentes:

```bash
uv run python cli.py importar --force
```

### 6. Gerar o índice RAG

```bash
uv run python cli.py rag index
```

Para verificar o status do índice:

```bash
uv run python cli.py rag status
```

### 7. Verificar status do banco

```bash
uv run python cli.py db status
```

Exibe total de registros nas tabelas principais e a última migration aplicada.

---

## Executando o Chatbot

### Interface Web (Streamlit)

```bash
uv run streamlit run ui/web.py
```

O app abre em `http://localhost:8501` por padrão.

### Interface CLI

```bash
uv run python -m ui
```

---

## Execução com Docker

O fluxo Docker executa `db init`, `importar` e `rag index` automaticamente no startup antes de subir o Streamlit.

### Deploy automático (recomendado)

```bash
docker compose build
docker compose up app
```

### Fluxo manual

```bash
docker compose build
docker compose run --rm app python cli.py db init
docker compose run --rm app python cli.py importar
docker compose run --rm app python cli.py rag index
docker compose up app
```

### Verificações em container

```bash
docker compose run --rm app python cli.py db status
docker compose run --rm app python cli.py rag status
```

### Persistência de dados

O volume `app_runtime` (montado em `/app/runtime`) preserva o banco SQLite e o índice Chroma entre restarts. Sem esse volume, a aplicação perde os dados a cada recriação do container.

Para desativar o bootstrap automático em um ambiente onde o banco já está pronto:

```env
AUTO_BOOTSTRAP_ON_START=0
```

Para o guia completo de Docker, consulte [docs/docker.md](./docker.md).

---

## Adicionando Novos Dados

Para adicionar um novo tipo de arquivo ao pipeline de ingestão:

1. Criar parser em `ingestion/parsers/xml/` ou `ingestion/parsers/csv/`, retornando `list[dict]` e usando a camada compartilhada de leitura e sanitização.
2. Criar modelo SQLAlchemy correspondente em `database/models/`.
3. Criar migration Alembic: `uv run alembic revision --autogenerate -m "add_novo_tipo"`.
4. Registrar o módulo em `ingestion/modules/` seguindo o padrão dos existentes.
5. Registrar no mapeamento de `ingestion/pipeline.py`.

Para referência completa do pipeline, consulte [docs/importacao.md](./importacao.md).
