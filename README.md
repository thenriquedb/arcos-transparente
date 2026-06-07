# Arcos Transparente

Sistema de importação e normalização de dados públicos da prefeitura de Arcos em banco de dados SQLite.

## Início Rápido

### 1. Instalar dependências

```bash
uv sync
```

### 2. Criar o arquivo `.env`

```bash
cp .env.example .env
```

Preencha ou ajuste no `.env`:

```env
DATABASE_URL=sqlite:///database/transparencia.db
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=sua_chave_aqui
```

`LLM_PROVIDER` deve permanecer como `openai` nesta fase. O `.env.example`
ja traz um modelo OpenAI recomendado; altere `OPENAI_MODEL` apenas se quiser
usar outro modelo OpenAI suportado.

### 3. Inicializar banco de dados

```bash
uv run python cli.py db init
```

### 4. Importar dados

```bash
uv run python cli.py importar
```

### 5. Gerar o índice RAG local do acervo markdown

```bash
uv run python cli.py rag index
```

Para verificar se o indice esta pronto:

```bash
uv run python cli.py rag status
```

## Sumário Da Documentação

- [INSTRUCTIONS.md](./INSTRUCTIONS.md): guia geral do projeto, ambiente, comandos, modelagem e operação
- [Guia Docker](./docs/docker.md): fluxo oficial de containerização com Docker e persistência local
- [Contexto para Codex CLI](./docs/codex-cli-contexto.md): resumo atual do projeto, decisoes tecnicas e pontos de atencao para novas sessoes
- [Arquitetura de agent e tools](./docs/arquitetura-agent-tools.md): visão da arquitetura híbrida com router, registry e tools públicas
- [Prompt do agente](./docs/agent-system-prompt.md): instruções de sistema usadas pelo assistente em produção
- [Acervo markdown local](./data/rag): conteúdo curado usado pelo RAG markdown-first do chatbot
- [Guia curto para novas regras do router](./docs/router-regras.md): como evoluir o roteamento sem quebrar prioridade nem espalhar lógica
- [Modelagem de banco](./docs/database.md): visão das tabelas, relacionamentos e decisões de persistência
- [Fluxo de importação](./docs/importacao.md): pipeline de ingestão, validação e carga dos dados
- [Helpers compartilhados](./docs/shared-helpers.md): regra de colocação para helpers globais versus helpers locais por subsistema
- [Perguntas de teste do agente](./docs/perguntas-teste-agente.md): conjunto de perguntas para validação manual do comportamento do agente

## Dados Cobertos

- **Contratos** - contratos administrativos, fornecedores e valores contratados
- **Licitações** - processos licitatorios, vencedores e valores estimados
- **Planejamento** - planejamento orcamentario da saude e da prefeitura
- **Despesas** - empenhos, restos a pagar, documentos extras, itens e comprovantes
- **Patrimônios** - bens patrimoniais, localização, situação e valores
- **Quadro de pessoal** - vagas criadas e preenchidas por regime de contratação
- **Folha de Pagamento** - historico mensal de pagamentos por servidor
- **Servidores** - quadro de pessoal, cargos, secretarias e salarios base
- **Receitas** - arrecadacao e lancamentos
- **Frotas** - veiculos e despesas da frota

## Requisitos

- Python 3.13+
- `uv` (gerenciador de pacotes)

Para instalar `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Ou via Homebrew:

```bash
brew install uv
```

## Execução Com Docker

O repositório agora inclui `Dockerfile`, `compose.yaml` e um entrypoint para
subir a interface Streamlit por padrão. O guia completo está em
[docs/docker.md](./docs/docker.md).

Para deploy automatizado, subir o container já executa `db init`, `importar` e
`rag index` antes de abrir o Streamlit:

```bash
docker compose build
docker compose up app
```

Se quiser rodar as rotinas manualmente, o fluxo continua disponível:

```bash
docker compose build
docker compose run --rm app python cli.py db init
docker compose run --rm app python cli.py importar
docker compose run --rm app python cli.py rag index
docker compose up app
```

Observacoes importantes:

- o fluxo usa uma unica instancia stateful
- o volume `app_runtime` preserva banco SQLite e indice RAG
- por padrao, o startup do container roda `db init`, `importar` e `rag index`
- voce pode desativar esse bootstrap automatico com `AUTO_BOOTSTRAP_ON_START=0`
- voce pode sobrescrever os defaults do Docker com `DOCKER_PORT`, `DOCKER_DATABASE_URL` e `DOCKER_RAG_PERSIST_DIRECTORY`

## Estrutura do Projeto

```
arcos-transparente/
├── cli.py                    # Interface de linha de comando
├── main.py                   # Entrypoint principal
├── alembic.ini              # Configuração de migrations
├── pyproject.toml           # Dependências do projeto
├── database/                # Modelos e banco de dados
│   ├── models/              # Modelos SQLAlchemy
│   ├── session.py           # Configuração de sessão
│   └── migrations/          # Scripts de migration
├── ingestion/               # Pipeline de importação
│   ├── pipeline.py          # Orquestração
│   ├── loaders/             # Loaders (SQL, etc)
│   └── parsers/             # Parsers XML por domínio
└── data/                    # Dados XML para importação
    └── xml/                 # Arquivos XML por tipo
```

## Licença

AGPL
