# INSTRUCTIONS.md

## Visão Geral

Este projeto importa dados públicos do portal da transparência para um banco SQLite normalizado, com foco em:

- integridade de dados (ACID)
- rastreabilidade (migrations versionadas)
- performance de consulta (índices)
- base pronta para consultas analíticas e IA

Os dados XML atualmente cobertos incluem:

- contratos
- licitações
- frotas
- receitas (arrecadação e lançamento)
- folha de pagamento
- servidores
- planejamento de despesas
- documentos de despesa (empenhos, restos a pagar e documentos extras)
- patrimônios
- quadro de pessoal

---

## Requisitos

- Python 3.13+
- `uv` (gerenciador de pacotes Python)

Para instalar `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Ou via Homebrew:

```bash
brew install uv
```

Instalação rápida de dependências:

```bash
uv sync
```

Este comando irá instalar todas as dependências especificadas em `pyproject.toml` em um ambiente virtual isolado.

---

## Configuração de ambiente

Crie `.env` na raiz:

```env
DATABASE_URL=sqlite:///database/transparencia.db
```

Para o chatbot web, use tambem:

```env
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=sua_chave_openai_aqui
```

---

## Execução com Docker

O repositório agora inclui `Dockerfile`, `compose.yaml` e
`docker/entrypoint.sh` para o fluxo oficial de containerização. A referência
operacional completa está em `docs/docker.md`.

Fluxo operacional recomendado:

```bash
docker compose build
docker compose run --rm app python cli.py db init
docker compose run --rm app python cli.py importar
docker compose run --rm app python cli.py rag index
docker compose up app
```

Overrides opcionais para o runtime Docker:

```env
DOCKER_PORT=8501
DOCKER_DATABASE_URL=sqlite:////app/runtime/database/transparencia.db
DOCKER_RAG_PERSIST_DIRECTORY=/app/runtime/vector_store/knowledge_markdown
```

Notas operacionais:

- o volume persistente do container deve preservar `/app/runtime`
- a implementação atual e de instancia unica stateful
- a importacao continua recriando toda a base antes da carga
- o entrypoint do container prepara os diretórios de runtime antes de subir o app

---

## Estrutura do projeto

```text
.
├── cli.py
├── alembic.ini
├── database/
│   ├── models/
│   └── migrations/
│       └── versions/
├── ingestion/
│   ├── pipeline.py
│   ├── loaders/
│   │   └── sql_loader.py
│   └── parsers/
│       └── xml/
│           ├── contratos_parser.py
│           ├── licitacoes_parser.py
│           ├── frotas_parser.py
│           ├── receitas_parser.py
│           ├── folha_pagamento_parser.py
│           └── servidores_parser.py
└── data/
    └── xml/
```

---

## Banco e migrations

Documentação do schema:

```bash
docs/database.md
```

Aplicar migrations:

```bash
uv run alembic upgrade head
```

Verificar revisão aplicada:

```bash
uv run python cli.py db status
```

---

## Comandos principais

### Inicializar banco

```bash
uv run python cli.py db init
```

### Status do banco

```bash
uv run python cli.py db status
```

### Importar tudo

```bash
uv run python cli.py importar
```

### Importar por tipo

```bash
uv run python cli.py importar --tipo licitacoes
uv run python cli.py importar --tipo frotas
uv run python cli.py importar --tipo receitas
uv run python cli.py importar --tipo folha_pagamento
uv run python cli.py importar --tipo despesas
uv run python cli.py importar --tipo patrimonios
uv run python cli.py importar --tipo quadro_pessoal
```

### Importar por ano

```bash
uv run python cli.py importar --tipo receitas --ano 2025
```

### Reimportar limpando dados

```bash
uv run python cli.py importar --tipo licitacoes --force
```

Observação:

Na POC atual, o comando `importar` recria toda a base SQLite antes de executar a carga.
O `--force` foi mantido apenas por compatibilidade.

---

## Tipos disponíveis no pipeline

- `contratos`
- `licitacoes`
- `frotas`
- `receitas`
- `folha_pagamento`
- `servidores`
- `planejamentos`
- `despesas`
- `patrimonios`
- `quadro_pessoal`

---

## Modelagem (resumo)

### Licitações

- `licitacoes`
- `vencedores_licitacao`
- `instrumentos_contratuais`
- `materias_instrumento`
- `fornecedores`

### Frotas

- `frota_veiculos`
- `frota_despesas`

### Contratos

- `contratos`
- `fornecedores`

### Receitas

- `receita_naturezas`
- `receita_arrecadacoes`
- `receita_lancamentos`

### Folha

- `servidores`
- `folha_servidores`
- `folha_lotacoes`
- `folha_cargos`
- `folha_pagamentos`

### Despesas, Patrimônio e Quadro

- `planejamento_despesas`
- `despesa_documentos`
- `despesa_documento_itens`
- `despesa_documentos_comprobatorios`
- `patrimonios`
- `quadro_pessoal`

Para a visão completa de tabelas, relacionamentos e objetivos de cada domínio, consulte `docs/database.md`.

---

## Garantias ACID e consistência

- transações explícitas nos processos de carga
- rollback em falha por lote/registro
- chaves únicas para evitar duplicatas
- chaves estrangeiras para integridade relacional
- SQLite com pragmas de integridade/concorrência configurados

---

## Boas práticas operacionais

1. Sempre rode `alembic upgrade head` antes de importar.
2. Na POC atual, considere que toda importação já faz recarga total da base.
3. Após cada importação, valide via `python3 cli.py db status`.
4. Mantenha logs habilitados para auditoria de erros.
5. Não edite tabelas manualmente fora do fluxo de migration/import.

---

## Troubleshooting rápido

### `ModuleNotFoundError`

Verifique se o arquivo parser existe no caminho esperado em `ingestion/parsers/xml/`.
Se você acabou de clonar o repositório, certifique-se de rodar `uv sync` primeiro.

### Migration não aplicada

Execute:

```bash
uv run alembic upgrade head
```

### Erro de tipo em valor monetário/data

Confirme se o parser está normalizando para:

- `Decimal` em valores monetários
- `YYYY-MM-DD` para datas

---

## Próximos passos recomendados

- criar testes automatizados para parsers e pipeline
- criar views SQL analíticas para consultas frequentes
- versionar snapshots de contagens para auditoria periódica
