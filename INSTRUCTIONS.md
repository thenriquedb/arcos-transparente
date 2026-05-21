# INSTRUCTIONS.md

## Visão Geral

Este projeto importa dados públicos do portal da transparência para um banco SQLite normalizado, com foco em:

- integridade de dados (ACID)
- rastreabilidade (migrations versionadas)
- performance de consulta (índices)
- base pronta para consultas analíticas e IA

Os dados XML atualmente cobertos incluem:

- licitações
- frotas
- receitas (arrecadação e lançamento)
- folha de pagamento

---

## Requisitos

- Python 3.9+
- `pip3`

Dependências principais:

- SQLAlchemy
- Alembic
- Typer
- Rich
- Loguru
- python-dotenv

Instalação rápida:

```bash
pip3 install sqlalchemy alembic typer rich loguru python-dotenv
```

---

## Configuração de ambiente

Crie `.env` na raiz:

```env
DATABASE_URL=sqlite:///database/transparencia.db
```

---

## Estrutura do projeto

```text
.
├── cli.py
├── alembic.ini
├── database/
│   ├── models.py
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

Aplicar migrations:

```bash
python3 -m alembic upgrade head
```

Verificar revisão aplicada:

```bash
python3 cli.py db status
```

---

## Comandos principais

### Inicializar banco

```bash
python3 cli.py db init
```

### Status do banco

```bash
python3 cli.py db status
```

### Importar tudo

```bash
python3 cli.py importar
```

### Importar por tipo

```bash
python3 cli.py importar --tipo licitacoes
python3 cli.py importar --tipo frotas
python3 cli.py importar --tipo receitas
python3 cli.py importar --tipo folha_pagamento
```

### Importar por ano

```bash
python3 cli.py importar --tipo receitas --ano 2025
```

### Reimportar limpando dados

```bash
python3 cli.py importar --tipo licitacoes --force
```

---

## Tipos disponíveis no pipeline

- `contratos`
- `licitacoes`
- `frotas`
- `receitas`
- `folha_pagamento`
- `servidores`

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

### Receitas

- `receita_naturezas`
- `receita_arrecadacoes`
- `receita_lancamentos`

### Folha

- `folha_servidores`
- `folha_lotacoes`
- `folha_cargos`
- `folha_pagamentos`

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
2. Use `--force` apenas quando quiser recarga total do domínio.
3. Após cada importação, valide via `python3 cli.py db status`.
4. Mantenha logs habilitados para auditoria de erros.
5. Não edite tabelas manualmente fora do fluxo de migration/import.

---

## Troubleshooting rápido

### `ModuleNotFoundError`

Verifique se o arquivo parser existe no caminho esperado em `ingestion/parsers/xml/`.

### Migration não aplicada

Execute:

```bash
python3 -m alembic upgrade head
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
