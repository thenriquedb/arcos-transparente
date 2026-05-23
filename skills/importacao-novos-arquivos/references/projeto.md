# Projeto

## Arquivos para ler primeiro

- `docs/importacao.md`
- `docs/database.md`
- `ingestion/pipeline.py`
- `ingestion/parsers/xml/`
- `ingestion/schemas/`
- `database/models/`
- `database/migrations/versions/`
- `tests/parsers/`
- `tests/schemas/`
- `tests/tools/sql_tools/`

## Exemplos uteis no estado atual

- Parser + schema com nested e descarte de filhos invalidos:
  - `ingestion/parsers/xml/licitacoes_parser.py`
  - `ingestion/schemas/licitacoes.py`
- Parser + schema simples com `mm/yyyy` convertido para `date`:
  - `ingestion/parsers/xml/servidores_parser.py`
  - `ingestion/schemas/servidores.py`
- Tool publica com linguagem leiga:
  - `agents/tools/sql_tools/folha_pagamento.py`
  - `agents/tools/sql_tools/servidores.py`

## Checklist de implementacao

1. Confirmar onde os XMLs novos entram em `data/xml/`.
2. Decidir se o dominio usa loader generico ou ramo dedicado em `ingestion/pipeline.py`.
3. Criar ou ajustar parser.
4. Criar ou ajustar schema Pydantic.
5. Criar ou ajustar modelo + migration.
6. Registrar no pipeline.
7. Criar testes.
8. Rodar smoke import por `tipo`.
9. Se houver consulta por agente, criar tool e schema da tool.

## Comandos uteis

```bash
UV_CACHE_DIR=.uv-cache uv run ruff check ingestion agents tests
UV_CACHE_DIR=.uv-cache uv run pytest -q tests/schemas tests/parsers tests/tools
UV_CACHE_DIR=.uv-cache uv run python cli.py db init
UV_CACHE_DIR=.uv-cache uv run python cli.py importar --tipo <tipo>
UV_CACHE_DIR=.uv-cache uv run python cli.py importar --tipo <tipo> --ano <ano>
```

## Padrões de validacao

- `clean_text` para `strip` e vazio para `None`
- `parse_decimal` para moeda e numeros
- `parse_date` para datas completas
- `parse_competencia_as_date` quando a fonte trouxer mes/ano
- `normalize_limit` e `validate_date_period` em tools SQL

## Coisas para nao repetir

- Nao duplicar helpers genericos de validacao dentro de schemas locais.
- Nao expor jargao tecnico desnecessario em tools publicas.
- Nao chamar `competencia` de `data_admissao`.
- Nao alterar migrations ou modelos sem refletir a semantica real do dado de origem.
