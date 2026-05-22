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

## Documentação Completa

Veja [INSTRUCTIONS.md](./INSTRUCTIONS.md) para documentação detalhada sobre:

- Configuração de ambiente
- Estrutura do projeto
- Comandos disponíveis
- Modelagem de dados
- Garantias ACID e consistência
- Boas práticas operacionais
- Troubleshooting

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
