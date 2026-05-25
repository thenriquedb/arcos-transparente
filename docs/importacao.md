# Importação de XML para SQLite

## Pré-requisitos

- Python 3.12+
- Dependências do projeto instaladas (`sqlalchemy`, `alembic`, `typer`, `rich`, `loguru`, `python-dotenv`)
- Arquivos XML disponíveis em `data/xml/`

## Configuração do `.env`

Crie um arquivo `.env` na raiz do projeto:

```env
DATABASE_URL=sqlite:///database/transparencia.db
```

## Primeira execução

1. Instale as dependências.
2. Configure o `.env`.
3. Rode as migrations:

```bash
python cli.py db init
```

4. Execute a importação:

```bash
python cli.py importar
```

## Referência de comandos CLI

### Inicializar banco e migrations

```bash
python cli.py db init
```

### Ver status do banco

```bash
python cli.py db status
```

Mostra:
- Total de registros em `contratos`, `licitacoes`, `servidores`, `planejamento_despesas` e demais tabelas principais
- Última migration aplicada

### Importar tudo

```bash
python cli.py importar
```

### Importar por tipo

```bash
python cli.py importar --tipo contratos
python cli.py importar --tipo licitacoes
python cli.py importar --tipo servidores
python cli.py importar --tipo planejamentos
```

### Importar por ano

```bash
python cli.py importar --ano 2024
```

### Reimportar apagando dados existentes

```bash
python cli.py importar --force
```

## Decisões de schema

- `Numeric(15, 2)` em valores monetários: evita erro de precisão binária de `Float`.
- `Date` em datas: permite filtros e ordenações corretas em SQL.
- Índices nos campos de consulta frequente: melhoram desempenho de filtros e agregações.
- Índices únicos compostos: evitam duplicatas em reimportações.
- Campos `criado_em` e `atualizado_em`: rastreabilidade e auditoria.

## Transações e consistência

- O loader executa importação em batches de 100 registros.
- Cada batch roda dentro de transação explícita.
- Em falha, ocorre rollback do batch.
- Erros são registrados com log detalhado via `loguru`.

## Como adicionar novo tipo de arquivo

1. Criar parser em `ingestion/parsers/xml/novo_tipo_parser.py` retornando `list[dict]`.
2. Criar modelo SQLAlchemy correspondente em `database/models.py`.
3. Criar migration Alembic para nova tabela/índices.
4. Registrar parser + modelo no mapeamento de `ingestion/pipeline.py`.
5. Opcional: expandir opção `--tipo` no CLI para incluir o novo tipo.
