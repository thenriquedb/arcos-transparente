# Arcos Transparente

Sistema de importação e normalização de dados públicos da prefeitura de Arcos em banco de dados SQLite.

## Início Rápido

### 1. Instalar dependências

```bash
uv sync
```

### 2. Inicializar banco de dados

```bash
uv run python cli.py db init
```

### 3. Importar dados

```bash
uv run python cli.py importar
```

## Sumário Da Documentação

- [INSTRUCTIONS.md](./INSTRUCTIONS.md): guia geral do projeto, ambiente, comandos, modelagem e operação
- [Arquitetura de agent e tools](./docs/arquitetura-agent-tools.md): visão da arquitetura híbrida com router, registry e tools públicas
- [Guia curto para novas regras do router](./docs/router-regras.md): como evoluir o roteamento sem quebrar prioridade nem espalhar lógica
- [Modelagem de banco](./docs/database.md): visão das tabelas, relacionamentos e decisões de persistência
- [Fluxo de importação](./docs/importacao.md): pipeline de ingestão, validação e carga dos dados
- [Perguntas de teste do agente](./docs/perguntas-teste-agente.md): conjunto de perguntas para validação manual do comportamento do agente

## Dados Cobertos

- 📋 **Licitações** - Processos licitatórios e fornecedores
- 🚗 **Frotas** - Veículos e despesas da frota
- 💰 **Receitas** - Arrecadação e lançamentos
- 💼 **Folha de Pagamento** - Servidores, lotações e cargos
- 👤 **Servidores** - Dados de servidores públicos

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

MIT
