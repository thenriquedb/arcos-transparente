# Skill: Ingestão de Novos Dados

Use esta skill quando precisar adicionar uma nova fonte de dados (CSV ou XML) ao pipeline de ingestão do Arcos Transparente.

## Visão Geral da Arquitetura

```
arquivo CSV/XML → parser → schema Pydantic → SQLLoader → SQLite
                                              (upsert por UniqueConstraint)
```

O pipeline é orientado a **tipos** (`tipo`). Cada tipo tem:
- Um **`_TipoDiscoverySpec`** em `ingestion/modules/discovery.py`
- Um **adapter** em `ingestion/modules/<tipo>.py`
- Um **parser** em `ingestion/parsers/csv/` ou `ingestion/parsers/xml/`
- Um **schema Pydantic** em `ingestion/schemas/<tipo>.py`
- Um **modelo ORM** em `database/models/`
- Uma **migration Alembic** em `database/migrations/versions/`

---

## Passo a Passo para um Novo Tipo CSV

### 1. Analisar o arquivo CSV

```python
# Verificar encoding, separador, layout das linhas
head -5 data/xml/<subdir>/<arquivo>.csv
python3 -c "
data = open('data/xml/<subdir>/<arquivo>.csv', 'rb').read()[:100]
for enc in ['utf-8', 'utf-8-sig', 'iso-8859-1']:
    try: print(enc, data.decode(enc)[:80]); break
    except: pass
"
```

Identificar:
- Linha de título (metadata, competência)
- Linha de cabeçalho
- Linhas de dados
- Linha de rodapé (ex: "PRONIM…")
- Separador (`;` ou `,`)
- Encoding (`utf-8` ou `iso-8859-1`)

### 2. Modelo ORM (`database/models/`)

Adicionar ao arquivo de modelo existente ou criar novo:
```python
class NovoModelo(Base):
    __tablename__ = "novo_tipo"
    __table_args__ = (
        UniqueConstraint("campo1", "campo2", name="uq_novo_tipo_campo1_campo2"),
        Index("ix_novo_tipo_campo1", "campo1"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # campos do domínio...
    campo_monetario: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    campo_data: Mapped[date | None] = mapped_column(Date, nullable=True)
    campo_texto: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

**Regras:**
- `Numeric(15,2)` para valores monetários (nunca `Float`)
- `Date` para datas
- `UniqueConstraint` obrigatória para o `SQLLoader` funcionar
- `criado_em`/`atualizado_em` obrigatórios

### 3. Exportar no `database/models/__init__.py`

```python
from database.models.meu_arquivo import NovoModelo
# Adicionar ao __all__
```

### 4. Schema Pydantic (`ingestion/schemas/<tipo>.py`)

```python
class NovoTipoInSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    competencia_referencia: date
    campo_texto: str | None = None
    campo_decimal: Decimal | None = None
    
    @field_validator("competencia_referencia", mode="before")
    @classmethod
    def _norm_comp(cls, v): return parse_competencia_as_date(v)
    
    @field_validator("campo_texto", mode="before")
    @classmethod
    def _norm_text(cls, v): return clean_text(v)
    
    @field_validator("campo_decimal", mode="before")
    @classmethod
    def _norm_dec(cls, v):
        r = parse_number(v)
        return Decimal(str(r)) if r is not None else None
```

Usar: `parse_competencia_as_date` (MM/YYYY→date), `parse_date` (DD/MM/YYYY), `clean_text`, `parse_number`.

### 5. Parser CSV (`ingestion/parsers/csv/<tipo>_parser.py`)

**Para CSV UTF-8:**
```python
from .shared import read_csv_text, clean_excel_csv_cell
import csv
from io import StringIO

def _parse_rows(filepath):
    text = read_csv_text(filepath, encoding="utf-8")
    reader = csv.reader(StringIO(text), delimiter=";")
    return [[clean_excel_csv_cell(c) for c in row] for row in reader]
```

**Para CSV ISO-8859-1 (portal legado):**
```python
from .shared import parse_semicolon_csv_rows
rows = parse_semicolon_csv_rows(filepath)  # lê com ISO-8859-1
```

**Detectar cabeçalho encoding-agnósticamente:**
```python
# Checar por colunas ASCII garantidas (ex: "nome", "codigo")
normalize_search_text(row[0]) == "nome"
# E largura mínima
len(non_empty) >= EXPECTED_WIDTH
```

**Extrair competência do título:**
```python
# Título: "...Arcos - 2025/01" → YYYY/MM → normalizar para MM/YYYY
a, b = part.split("/", 1)
if len(a) == 4:
    return f"{b}/{a}"  # YYYY/MM → MM/YYYY
```

**Para CSVs com células `="valor"` (Excel export):** `clean_excel_csv_cell` já cuida disso.

### 6. Discovery (`ingestion/modules/discovery.py`)

```python
# Em _DISCOVERY_SPECS:
"novo_tipo": _TipoDiscoverySpec("subdir", ("padrao-*.csv",)),

# Em _YEAR_FILTER_EXEMPT_TIPOS se o arquivo não carrega o ano no nome:
_YEAR_FILTER_EXEMPT_TIPOS = frozenset({..., "novo_tipo"})

# Adicionar função:
def discover_novo_tipo_files(data_dir, ano): return discover_files_for_tipo(data_dir, "novo_tipo", ano)
```

### 7. Módulo (`ingestion/modules/<tipo>.py`)

```python
from database.models import NovoModelo
from .adapters import build_model_loader_adapter
from .discovery import discover_novo_tipo_files

ADAPTER = build_model_loader_adapter(
    "novo_tipo",
    discover_files=discover_novo_tipo_files,
    parser_attr="novo_tipo_parser",  # nome do atributo em IngestionPipeline
    model=NovoModelo,
)
```

### 8. Registrar (`ingestion/modules/registry.py`)

```python
from .novo_tipo import ADAPTER as NOVO_TIPO_ADAPTER

def build_adapter_registry():
    return {
        ...,
        "novo_tipo": NOVO_TIPO_ADAPTER,
    }
```

### 9. Adicionar parser ao Pipeline (`ingestion/pipeline.py`)

```python
from ingestion.parsers.csv.novo_tipo_parser import NovoTipoParser

class IngestionPipeline:
    def __init__(self):
        ...
        self.novo_tipo_parser = NovoTipoParser()
```

### 10. Migration Alembic

```python
# database/migrations/versions/YYYYMMDD_NNNNNN_<descricao>.py
revision = "YYYYMMDD_NNNNNN"
down_revision = "<revision_anterior>"

def upgrade():
    op.create_table("novo_tipo", ...)
    op.create_index(...)

def downgrade():
    op.drop_index(...)
    op.drop_table("novo_tipo")
```

Numeração: `YYYYMMDD_000NNN` em sequência.

### 11. SQL Tools (se necessário para o agente)

Criar `agents/tools/sql_tools/<dominio>/` com:
- `__init__.py`
- `consultar_<dominio>_query.py` — tool principal com `@register(name=ToolName.CONSULTAR_X, scope=PUBLIC_SCOPE, routing=routing_metadata(examples=[...], hints=[...]))`
- `consultar_<dominio>_schema.py` — Params, Metadata, Response
- `agregar_<dominio>_query.py` (se aplicável)
- `agregar_<dominio>_schema.py` (se aplicável)
- `shared/filters.py` — FiltroSchema, ALLOWED_FIELDS, ALLOWED_SORT_FIELDS
- `shared/querying.py` — apply_filters(), resolve_mes_padrao(), project_fields()
- `shared/runtime.py` — serializar(), obter_mes_mais_recente()

**Atualizar `agents/tools/names.py`:**
```python
CONSULTAR_X = "consultar_x"
AGREGAR_X = "agregar_x"
```

**Atualizar `tests/tools/test_registry.py`:**
```python
# Adicionar nas duas listas e incrementar o count:
assert len(catalog) == <N + novo_total>
```

### 12. System Prompt (`docs/agent-system-prompt.md`)

Adicionar na seção `§5. Roteamento de Ferramentas`:
```markdown
### <Domínio novo>
- **Quando usar**: condições claras
- **Tool de lookup**: `consultar_x`
- **Tool de agregação**: `agregar_x`
- **NUNCA** confundir com...
```

---

## Testes

Criar fixtures em `tests/fixtures/<tipo>_sample.csv` e:

```python
# tests/parsers/test_<tipo>_parser.py
def test_parser_extrai_registros():
    parser = NovoTipoParser()
    registros = parser.parse("tests/fixtures/<tipo>_sample.csv")
    assert len(registros) == N
    assert registros[0]["campo"] == valor_esperado

def test_parser_rejeita_arquivo_invalido(tmp_path):
    ...pytest.raises(ValueError, match="...")

# tests/pipeline/test_<tipo>_pipeline.py — usa _build_session() + monkeypatch
def test_pipeline_importa_e_reimporta_sem_duplicar(monkeypatch, tmp_path):
    session = _build_session()
    @contextmanager
    def fake_get_session(): yield session
    monkeypatch.setattr(pipeline_module, "get_session", fake_get_session)
    pipeline = IngestionPipeline(data_dir=str(tmp_path))
    resultado = pipeline.run(tipos=["novo_tipo"])
    assert resultado["novo_tipo"].inseridos == N
    session.rollback()  # necessário antes do segundo run
    resultado2 = pipeline.run(tipos=["novo_tipo"])
    assert resultado2["novo_tipo"].atualizados + resultado2["novo_tipo"].ignorados == N
```

---

## Checklist Rápido

- [ ] Modelo ORM criado + exportado em `__init__.py`
- [ ] Migration criada com `upgrade()` e `downgrade()`
- [ ] Schema Pydantic criado
- [ ] Parser CSV criado
- [ ] Discovery spec adicionada
- [ ] Módulo adapter criado
- [ ] Registrado em `registry.py`
- [ ] Parser instanciado em `pipeline.py`
- [ ] SQL tools criadas (se necessário)
- [ ] `ToolName` atualizado
- [ ] `test_registry.py` atualizado (listas + count)
- [ ] System prompt atualizado
- [ ] Testes de parser + pipeline passando
- [ ] `uv run pytest -q` → tudo verde
- [ ] `uv run ruff check` → zero erros no código novo
