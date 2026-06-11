# Contribuindo

## Pré-requisitos de Desenvolvimento

- Python 3.13+
- `uv` instalado (veja [Primeiros Passos](./getting-started.md))
- Dependências de dev incluídas no grupo `[dependency-groups] dev` do `pyproject.toml`

```bash
uv sync
```

---

## Executando os Testes

```bash
uv run pytest
```

Para executar um subconjunto específico:

```bash
uv run pytest tests/parsers/
uv run pytest tests/agents/
uv run pytest tests/pipeline/
```

### Estrutura de Testes

| Diretório | Foco |
|-----------|------|
| `tests/parsers/` | Testes unitários de parsers XML e CSV por domínio |
| `tests/pipeline/` | Testes de integração do pipeline completo (parser + schema + loader) |
| `tests/loaders/` | Testes do `sql_loader` (batches, rollback, deduplicação) |
| `tests/agents/test_chatbot.py` | Boundary pré-modelo, bootstrap do agente e contrato conversacional |
| `tests/agents/test_guardrails.py` | Guardrails de escopo, injection e perguntas vazias |
| `tests/agents/test_hybrid_selection.py` | Seleção híbrida de tools |
| `tests/agents/test_intents.py` | Predicados de intenção determinísticos por domínio |
| `tests/nlu/` | Extractors e leitura de consulta (`QueryReading`) |

Para testes manuais de ponta a ponta do comportamento do agente, use o conjunto de perguntas em [`docs/perguntas-teste-agente.md`](./perguntas-teste-agente.md).

---

## Linting e Formatação

O projeto usa **Ruff** para análise estática e formatação.

```bash
# verificar
uv run ruff check .

# corrigir automaticamente
uv run ruff check --fix .

# formatar
uv run ruff format .
```

---

## Convenções de Branch e PR

- **Branches**: use o formato `feature/<descricao>`, `fix/<descricao>` ou `refactor/<descricao>`.
- **Commits**: mensagens em inglês, imperativo, sem ponto final. Ex: `feat: add receitas aggregation tool`.
- **PRs**: descreva o que mudou e por quê; inclua referência à issue se aplicável.
- Antes de abrir PR, garanta que `pytest` e `ruff check` passam sem erros.

---

## Adicionando uma Nova Tool Pública

1. Crie a pasta do domínio em `agents/tools/sql_tools/<dominio>/` seguindo a convenção:
   ```text
   agents/tools/sql_tools/<dominio>/
   ├── __init__.py
   ├── consultar_<dominio>_query.py   # tool de listagem
   ├── consultar_<dominio>_schema.py  # schema Pydantic de entrada
   ├── agregar_<dominio>_query.py     # tool de agregação
   ├── agregar_<dominio>_schema.py
   └── shared/
       ├── base.py
       ├── filters.py
       ├── querying.py
       └── runtime.py
   ```

2. Registre cada tool com o decorator `@register(...)` em `agents/tools/registry.py`, incluindo:
   - `scope=PUBLIC_SCOPE`
   - `tags` com `domain:<dominio>` e `shape:lookup` ou `shape:aggregate`
   - `routing.examples`: pelo menos duas perguntas representativas de cidadão
   - `routing.hints`: pistas curtas de seleção (domínio, forma de consulta, intenção)

3. A roteabilidade vem da `routing_metadata` da tool (`examples`/`hints`/`exclusions`) consumida pelo seletor híbrido — não há mais router determinístico a editar. Só adicione um predicado determinístico em `agents/nlu/intents.py` se a distinção for genuinamente ambígua e precisar de garantia testável (ex.: emenda vs. transferência).

4. Cubra com testes mínimos:
   - registry (a tool aparece em `get_public_tools()`)
   - schema (valida combinações inválidas de parâmetros)
   - tool pública (comportamento funcional com banco em memória)

---

## Convenções de Código

- **Sem comentários explicativos do óbvio.** Comente apenas invariantes não-óbvias ou workarounds com razão de existir.
- **Uma tool pública por capability ampla.** Variações de filtro, ordenação e agrupamento devem ser absorvidas pela tool existente, não virar tool nova.
- **Helpers compartilhados:** use `shared/` apenas para código realmente transversal entre subsistemas. Helpers locais a um domínio ficam em `<dominio>/shared/`. Consulte [`docs/shared-helpers.md`](./shared-helpers.md).
- **Valores monetários:** sempre `Numeric(15, 2)` no banco; nunca `Float`.
- **Datas:** sempre `Date` no banco; formato `YYYY-MM-DD` nos parsers.
- **Encoding XML:** respeite BOM e declaração `encoding` do cabeçalho; use `ISO-8859-1` como fallback explícito.

---

## Migrações de Banco

Para criar uma migration após alterar modelos SQLAlchemy:

```bash
uv run alembic revision --autogenerate -m "descricao_da_mudanca"
uv run alembic upgrade head
```

Para verificar o estado atual:

```bash
uv run python cli.py db status
```

Nunca edite tabelas manualmente fora do fluxo de migration/import.
