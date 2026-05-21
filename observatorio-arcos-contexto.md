# Arcos Transparente — Documento de Contexto do Projeto

## 1. Visão Geral

**Nome do projeto:** Arcos Transparente  
**Objetivo:** Aplicação de IA que permite ao cidadão fazer perguntas em linguagem natural sobre dados públicos do portal da transparência da cidade de Arcos (MG), obtendo respostas precisas sobre gastos, contratos, licitações e servidores municipais.  
**Público-alvo:** A definir (cidadãos, jornalistas, vereadores)  

---

## 2. Problema que resolve

O portal da transparência exporta dados em XML, formato difícil de consumir pelo cidadão comum. O projeto transforma esses dados em uma interface conversacional onde qualquer pessoa pode perguntar, por exemplo:

- *"Quanto foi gasto em saúde no primeiro trimestre de 2024?"*
- *"Quais fornecedores receberam mais de R$ 100 mil?"*
- *"Quais contratos vencem em junho?"*
- *"Quais contratos envolvem obras de pavimentação?"*

---

## 3. Stack Tecnológica

### Linguagem e gerenciamento de projeto
- **Python 3.12+**
- **pip** — gerenciador de dependências e ambiente virtual (substitui pip + venv)

### Ingestão e processamento de dados
- **lxml** — parsing de arquivos XML do portal da transparência
- **pydantic** — validação de schemas e tipagem dos dados

### Banco de dados estruturado
- **SQLite** — banco relacional local, sem servidor
- **SQLAlchemy ORM** — mapeamento objeto-relacional (modo classes, não Core)
- **Alembic** — controle de migrations e versionamento do schema

### Banco vetorial (RAG)
- **ChromaDB** — banco vetorial local para busca semântica
- **sentence-transformers** — geração de embeddings em português  
  Modelo: `intfloat/multilingual-e5-large`

### IA e orquestração
- **LangChain** — framework principal de orquestração do agente
- **GPT** — execução de LLMs localmente (sem custo, sem envio de dados)  
  Modelo recomendado: `gpt-4`

### Interface
- **FastAPI** — API REST para integração futura
- **Typer** — CLI para comandos de importação e administração
- **Rich** — output formatado no terminal (barras de progresso, logs)

### Utilitários
- **python-dotenv** — gerenciamento de variáveis de ambiente
- **loguru** — sistema de logs simplificado

---

## 4. Arquitetura

### Fluxo de dados

```
XMLs do portal da transparência
          │
          ▼
[Parsers — um por formato/tipo de arquivo]
          │
          ├──► [SQLite via SQLAlchemy]     ← dados estruturados
          │              │
          │         [sql_tool]             ← Text-to-SQL via LangChain
          │
          └──► [ChromaDB]                  ← resumos textuais
                         │
                    [rag_tool]             ← busca semântica
                         │
          ┌──────────────┘
          │
    [Agente LangChain]                     ← decide qual tool usar
          │
    [LLM via Ollama]                       ← gera resposta em português
          │
    [Streamlit / FastAPI]                  ← entrega ao usuário
```

### Decisão SQL vs RAG

| Tipo de pergunta | Tool utilizada |
|---|---|
| Somatórios, totais, médias | `sql_tool` |
| Filtros por data, período | `sql_tool` |
| Rankings e comparações | `sql_tool` |
| Busca por CNPJ específico | `sql_tool` |
| Perguntas abertas sobre conteúdo | `rag_tool` |
| Explicações e contexto | `rag_tool` |

O agente LangChain decide automaticamente qual tool usar baseado na **descrição (docstring) de cada tool** — essa descrição é injetada no prompt enviado ao LLM.

---

## 5. Estrutura de Pastas

```
observatorio-arcos/
│
├── pyproject.toml                  # dependências (gerenciado pelo pip)
├── .env                            # chaves de API e configurações locais
├── .env.example                    # template do .env para compartilhar
├── README.md
│
├── data/                           # arquivos brutos baixados do portal
│   ├── xml/
│   ├── csv/                        # pronto para o futuro
│   └── pdf/                        # pronto para o futuro
│
├── ingestion/                      # transforma dado bruto em dado útil
│   ├── parsers/
│   │   ├── base_parser.py          # classe base abstrata (ABC)
│   │   ├── xml/
│   │   │   ├── contratos_parser.py
│   │   │   ├── licitacoes_parser.py
│   │   │   └── servidores_parser.py
│   │   ├── csv/                    # futuro
│   │   └── pdf/                    # futuro
│   ├── loaders/
│   │   ├── sql_loader.py           # persiste no SQLite
│   │   └── vector_loader.py        # persiste no ChromaDB
│   └── pipeline.py                 # orquestra parsers + loaders
│
├── database/
│   ├── models.py                   # schema das tabelas (SQLAlchemy ORM)
│   ├── migrations/                 # histórico de alterações (Alembic)
│   └── transparencia.db            # banco gerado (não versionar)
│
├── vector_store/
│   └── chroma_db/                  # banco vetorial gerado (não versionar)
│
├── agent/
│   ├── tools/
│   │   ├── sql_tool.py             # tool de consulta SQL
│   │   └── rag_tool.py             # tool de busca vetorial
│   ├── prompts.py                  # todos os prompts do sistema
│   └── agent.py                    # monta e exporta o agente principal
│
├── api/
│   ├── main.py
│   └── routes/
│       └── perguntas.py
│
├── app/
│   └── main.py                     # interface Streamlit
│
├── cli.py                          # comandos de administração (Typer)
│
└── tests/
    ├── test_parsers.py
    ├── test_tools.py
    └── test_agent.py
```

---

## 6. Padrões e Decisões de Projeto

### Parsers extensíveis
Todos os parsers herdam de `BaseParser` (ABC), garantindo interface consistente independente do formato:

```python
class BaseParser(ABC):
    @abstractmethod
    def parse(self, filepath: str) -> list[dict]: ...

    @abstractmethod
    def validate(self, record: dict) -> bool: ...
```

Para adicionar um novo formato (ex: CSV), basta criar `CsvParser(BaseParser)` — o restante do sistema não muda.

### Banco de dados
- **ACID garantido** via transações explícitas do SQLAlchemy
- **Upsert** implementado para evitar duplicatas em reimportações
- **Índices** nos campos mais consultados: data, categoria, secretaria, cnpj
- **Schema semântico** — nomes de campos descritivos para melhorar a qualidade do Text-to-SQL
- **Migrations com Alembic** — todo schema change versionado e rastreável

### Tool calling (LangChain)
- Cada tool tem docstring detalhada que o LLM usa para decidir quando chamá-la
- `AgentExecutor` com `verbose=True` durante desenvolvimento para rastrear decisões
- `max_iterations=5` para evitar loops infinitos

### LLM local
- Ollama roda localmente no Mac M4 — zero custo, zero envio de dados externos
- Modelo: `qwen2.5:14b` (cabe nos 16 GB de memória unificada do M4)
- Embeddings: `intfloat/multilingual-e5-large` via sentence-transformers (local)

---

## 7. CLI — Comandos Planejados

```bash
# Inicializar banco e rodar migrations
python cli.py db init

# Importar todos os arquivos de data/
python cli.py import all

# Importar tipo específico
python cli.py import --tipo contratos --ano 2024

# Reimportar forçando sobreescrita
python cli.py import all --force

# Verificar status do banco
python cli.py db status
```