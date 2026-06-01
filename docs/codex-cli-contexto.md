# Contexto Atual do Projeto para Codex CLI

Atualizado com base no codigo do repositorio em 2026-06-01.

## Objetivo

`arcos-transparente` e uma base Python para importar dados publicos do portal da transparencia de Arcos (MG), normalizar esses dados em SQLite e expor consultas em linguagem natural por meio de um agente com tools SQL.

O foco atual do projeto e:

- ingestao confiavel de XMLs publicos
- modelagem relacional auditavel
- consulta estruturada via tools publicas amplas
- orquestracao guiada pelo LLM com guardrails determinísticos antes do modelo

## Resumo Executivo

Hoje o projeto funciona mais como uma pilha de **XML -> parser -> schema -> SQLite -> tools SQL -> agente LangChain** do que como uma aplicacao web completa.

O estado real do codigo neste momento e:

- CLI operacional para banco e importacao em `cli.py`
- pipeline de ingestao em `ingestion/pipeline.py`
- modelos SQLAlchemy em `database/models/`
- migrations Alembic em `database/migrations/versions/`
- chatbot em `agents/chatbot/`, com CLI e interface web local em Streamlit
- router de compatibilidade em `agents/router.py` e `agents/routing/`
- tools SQL publicas em `agents/tools/sql_tools/`
- bootstrap principal do agente em `agents/chatbot/agent.py`

Nao ha, no codigo ativo, uma API web de producao pronta nem uma integracao RAG/Chroma em uso pelo agente principal.

## Stack Atual

- Python 3.13+
- `uv` para ambiente e execucao
- Typer + Rich para CLI
- SQLAlchemy 2 + Alembic para banco e migrations
- Pydantic 2 para validacao de schemas
- LangChain + LangGraph + OpenAI para o agente
- SQLite local como banco principal

## Dominios Cobertos

O pipeline cobre estes tipos de importacao:

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
- `eleitos`

As consultas do agente hoje se concentram nestes dominios publicos:

- servidores
- folha de pagamento historica de pessoa especifica
- contratos
- licitacoes
- receitas
- planejamento
- despesas
- patrimonios
- quadro de pessoal
- eleitos
- frota

## Superficie Publica do Agente

O projeto tomou a decisao de expor poucas tools amplas, em vez de muitas tools estreitas. A superficie publica atual tem 19 tools:

- `consultar_servidores`
- `agregar_servidores`
- `consultar_contratos`
- `agregar_contratos`
- `consultar_licitacoes`
- `agregar_licitacoes`
- `consultar_receitas`
- `agregar_receitas`
- `consultar_planejamento`
- `agregar_planejamento`
- `consultar_despesas`
- `agregar_despesas`
- `consultar_patrimonios`
- `agregar_patrimonios`
- `consultar_quadro_pessoal`
- `agregar_quadro_pessoal`
- `consultar_eleitos`
- `consultar_frota`
- `buscar_historico_de_pagamentos_do_servidor`

Decisao importante: a variacao da pergunta deve ser absorvida por filtros, ordenacao, agregacao e projecao de campos, nao pela criacao de novas tools por caso de uso.

## Fluxo Principal

1. O CLI ou a rotina de manutencao dispara a importacao.
2. `IngestionPipeline` descobre arquivos XML por tipo e ano.
3. Parsers em `ingestion/parsers/xml/` transformam XML em registros Python.
4. Schemas em `ingestion/schemas/` validam e normalizam os dados.
5. Loaders persistem no SQLite com upsert e relacionamentos.
6. O agente recebe uma pergunta.
7. O runtime do chatbot aplica respostas locais e guardrails hard-coded antes de invocar o modelo.
8. Para consultas permitidas, o agente LangChain recebe a superficie publica ampla de tools e orquestra a execucao via prompt e contratos das tools.

## Decisoes Tecnicas Ja Tomadas

### 1. Banco local em SQLite, com pragmas explicitos

O engine e criado em `database/session.py` com:

- `journal_mode=WAL`
- `foreign_keys=ON`
- `synchronous=NORMAL`

Isso mostra uma escolha clara por simplicidade operacional local, com integridade relacional e concorrencia razoavel para a fase atual.

### 2. Importacao recria a base inteira

`cli.py importar` sempre recria o banco antes de carregar os XMLs. O flag `--force` foi mantido, mas hoje e redundante.

Implicacao pratica:

- a importacao atual e pensada como recarga total
- o fluxo favorece consistencia global sobre ingestao incremental

### 3. Loader generico + ramos especializados

Existe um `SQLLoader` generico em `ingestion/loaders/sql_loader.py` que faz upsert com base na primeira `UniqueConstraint` do modelo.

Mas alguns dominios usam carga especializada em `ingestion/pipeline.py` porque precisam preservar relacionamentos ou montar entidades filhas:

- contratos
- licitacoes
- despesas
- receitas
- frotas
- folha de pagamento

### 4. Rastreabilidade acima de simplificacao excessiva

O projeto preserva dados textuais de origem e, em alguns casos, tambem granularidade do XML.

Exemplo forte:

- `Contrato` guarda `fornecedor` e `cnpj` textuais
- tambem aponta para `fornecedor_id` canonico quando possivel
- preserva `xml_original` para auditoria
- mantem tabelas filhas para despesas orcamentarias e itens adquiridos

### 5. Router deterministico antes do LLM

O router deterministico ainda existe, mas hoje ele deve ser tratado como
compatibilidade e apoio a testes legados. Ele:

- normaliza o texto
- detecta dominio e tipo de operacao quando algum fluxo ainda pede isso
- compartilha as mesmas regras hard-coded de bloqueio para prompt injection,
  pergunta vazia e fora de escopo
- nao e a camada autoritativa para interpretar perguntas permitidas no chatbot atual

No chatbot atual, perguntas permitidas seguem o system prompt e os contratos das
tools. O router nao deve substituir essas camadas nem impor comportamento
conversacional concorrente.

### 6. OpenAI e o caminho oficial desta fase

O bootstrap principal em `agents/chatbot/agent.py` usa:

- `LLM_PROVIDER` ou `MODEL_PROVIDER`
- `OPENAI_MODEL`, com padrao `gpt-4.1`
- `OPENAI_API_KEY`

Hoje o provider real implementado no bootstrap principal e `ChatOpenAI`.

### 7. Prompt versionado em arquivo

`agents/chatbot/agent.py` carrega o prompt de sistema a partir de
`docs/agent-system-prompt.md`.

Isso e uma boa decisao de manutencao porque separa o comportamento do agente do codigo Python e deixa o prompt versionado e revisavel.

## Pontos de Atencao

### 1. Ha documentacao historica desatualizada

O arquivo `observatorio-arcos-contexto.md` na raiz descreve uma arquitetura antiga com RAG, Chroma, FastAPI e Ollama. Isso nao reflete o codigo principal atual e nao deve ser tratado como fonte de verdade do estado presente.

### 2. Parte da documentacao antiga ainda fala em `main.py`

O bootstrap canonico do agente cidadao hoje esta em:

- `agents/chatbot/agent.py`
- `agents/chatbot/core.py`

Se algum documento mencionar `main.py`, `tests/test_main.py` ou subconjunto de
tools como runtime principal, trate isso como contexto historico e prefira os
modulos de chatbot e seus testes atuais.

### 3. Pasta `data/rag/` nao significa RAG ativo

Ha arquivos de apoio em `data/rag/`, mas nao existe hoje uma pipeline ativa de embeddings, Chroma ou `rag_tool` integrada ao agente principal.

## Arquivos para Ler Primeiro

Se o objetivo for entender o projeto rapido no Codex CLI, esta ordem funciona bem:

1. `README.md`
2. `docs/codex-cli-contexto.md`
3. `cli.py`
4. `ingestion/pipeline.py`
5. `database/models/__init__.py`
6. `docs/database.md`
7. `agents/chatbot/agent.py`
8. `agents/chatbot/core.py`
9. `docs/arquitetura-agent-tools.md`
10. `tests/agents/test_chatbot.py`

## Comandos Uteis

```bash
uv sync
uv run python cli.py db init
uv run python cli.py importar
uv run python cli.py db status
uv run pytest -q
uv run python chat_playground.py
```

Se quiser limitar a importacao:

```bash
uv run python cli.py importar --tipo contratos --ano 2025
```

## O Que Nao Assumir Sem Conferir

- nao assumir que existe API web pronta
- nao assumir que existe RAG em producao
- nao assumir que a importacao e incremental
- nao assumir que o router define o comportamento principal do chatbot
- nao assumir que docs antigos da raiz descrevem o estado atual

## Sinais de Qualidade do Projeto

- cobertura de testes distribuida em CLI, router, parsers, schemas, pipeline e tools
- uso consistente de `UniqueConstraint` para upsert
- migrations versionadas por dominio
- separacao clara entre parsing, schema, persistencia e consulta

No momento desta leitura, o repositorio tem 67 arquivos de teste.

## Melhor Forma de Trabalhar Aqui

Se voce for evoluir o projeto no Codex CLI, o caminho mais seguro costuma ser:

1. confirmar o dominio afetado
2. localizar parser, schema, modelo, migration e tool correspondentes
3. ajustar testes primeiro ou junto da mudanca
4. validar se o router tambem precisa evoluir
5. revisar se a mudanca afeta documentacao em `docs/`

Esse repositorio ja esta organizado o bastante para crescer por dominio. A principal disciplina necessaria e manter alinhados parser, modelo, migration, tool publica e testes.
