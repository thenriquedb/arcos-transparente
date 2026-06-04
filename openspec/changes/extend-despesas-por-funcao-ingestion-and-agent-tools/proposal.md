## Why

O repositorio ja possui um CSV publico em `data/xml/despesas/despesas-por-funcao/`, mas esse relatorio ainda nao entra no fluxo normal de importacao para SQLite nem pode ser consultado pelo agente por meio de tools dedicadas. Isso deixa sem contrato local um conjunto importante de perguntas sobre dotacao, creditos adicionais, empenhado, liquidado e pago por funcao.

## What Changes

- Estender a ingestao para descobrir arquivos suportados de `despesas-por-funcao`, interpretar o cabecalho/metadados do relatorio e normalizar as linhas agregadas por funcao.
- Criar persistencia SQL dedicada para esse relatorio em uma nova tabela, em vez de forcar o contrato em `planejamento_despesas` ou `despesa_documentos`.
- Adicionar tools publicas de consulta e agregacao para `despesas-por-funcao`, com filtros e metricas alinhados ao relatorio.
- Integrar as novas tools ao registro publico, aos contratos de prompt/roteamento e aos testes de regressao para perguntas estruturadas sobre despesas por funcao.
- Documentar a fronteira semantica entre `despesas-por-funcao`, `planejamento` e `despesas` documentais.

## Capabilities

### New Capabilities
- `despesas-por-funcao-source-ingestion`: Descobre arquivos CSV suportados de `despesas-por-funcao`, extrai metadados do relatorio e persiste linhas por funcao em armazenamento SQL dedicado com reimportacao idempotente.
- `public-despesas-por-funcao-agent-access`: Expoe os dados importados de `despesas-por-funcao` por meio de tools SQL publicas e integracao com o agente para consultas e agregacoes sobre o relatorio por funcao.

### Modified Capabilities
- None.

## Impact

- Affected code: `ingestion/pipeline.py`, novos parsers/schemas CSV para `despesas-por-funcao`, `database/models/`, migrations em `database/migrations/versions/`, novas tools em `agents/tools/sql_tools/`, integracao em `agents/routing/`, `docs/` e suites de teste relacionadas.
- Affected systems: descoberta de arquivos de ingestao, persistencia SQL local, superficie publica do agente e documentacao da base.
- Affected behavior: quais relatorios de `despesas-por-funcao` passam a ser carregados automaticamente, quais metricas ficam consultaveis e como o agente responde perguntas estruturadas sobre gasto agregado por funcao.
- Risk areas: sobreposicao semantica com `planejamento`, parsing de CSV exportado com ruido de cabecalho/rodape, deduplicacao em reimportacoes e ambiguidade entre perguntas de `despesas`, `planejamento` e o novo dominio agregado.
