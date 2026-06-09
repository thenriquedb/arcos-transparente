# Arcos Transparente Context

This context captures the project language for ingestao de dados publicos municipais and the citizen-facing query surface built on top of that base.

## Language

**Tipo de importacao**:
The import unit exposed by the CLI and the pipeline, such as `contratos`, `despesas`, `servidores` or `transferencias_financeiras`. A tipo owns file discovery, parsing, persistence and import reporting for one supported source family.
_Avoid_: parser, tabela, formato

**Modulo de ingestao**:
The module that implements one `tipo de importacao`. It owns file discovery, parsing, persistence, transaction policy and import reporting for that tipo.
_Avoid_: pipeline step, loader wrapper

**Leitura de consulta** (`QueryReading`):
The structured facts read from a citizen question once — year, name, public object, secretaria, domain hints, scope signals. Produced by `read_query` in `agents/routing/reading.py`, which is the deep interface over the private `_extract_*` functions in `agents/routing/extractors.py`. Guardrails and tool selection consume a `QueryReading` instead of re-parsing the question with regex.
_Avoid_: parse result, extracted entities, NLU output
