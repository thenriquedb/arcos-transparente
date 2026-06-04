## Why

O repositório já possui arquivos relevantes em `data/xml/transferencias-financeiras/`, mas esse conteúdo ainda não entra no fluxo normal de importação para SQLite nem pode ser consultado pelo agente. Isso deixa fora da base local um conjunto importante de perguntas cidadãs sobre transferências para a Câmara, movimentações financeiras associadas e emendas parlamentares destinadas ao município.

## What Changes

- Estender a ingestão para descobrir, interpretar e persistir os arquivos do diretório `transferencias-financeiras`, cobrindo tanto os XMLs de recebimentos/movimentos quanto o CSV de emendas parlamentares.
- Criar persistência própria em SQL para esse domínio, com tabelas dedicadas em vez de reaproveitar `receitas` ou `despesas` de forma inadequada.
- Definir como os dois formatos de fonte serão normalizados, preservando rastreabilidade, campos monetários, datas, unidades gestoras e metadados públicos úteis para consulta.
- Adicionar tools públicas de consulta e agregação para perguntas estruturadas sobre transferências financeiras e emendas parlamentares.
- Integrar o novo domínio ao agente, incluindo registro das tools, contratos de prompt, roteamento compatível e testes de regressão.

## Capabilities

### New Capabilities
- `transferencias-financeiras-source-ingestion`: Descobre os arquivos suportados em `transferencias-financeiras`, parseia XMLs de movimentação e CSVs de emendas, e persiste os dados em tabelas SQL dedicadas com comportamento idempotente de reimportação.
- `public-transferencias-financeiras-agent-access`: Expõe transferências financeiras e emendas parlamentares por meio de tools públicas e integração com o agente, permitindo consultas estruturadas, totais e rankings a partir da base local.

### Modified Capabilities
- None.

## Impact

- Affected code: `ingestion/pipeline.py`, novos parsers em `ingestion/parsers/xml/` e/ou `ingestion/parsers/csv/`, novos modelos em `database/models/`, migrations em `database/migrations/versions/`, novas tools em `agents/tools/sql_tools/`, integração em `agents/chatbot/`, `agents/router.py` e possivelmente regras em `agents/routing/`.
- Affected systems: descoberta de arquivos de ingestão, persistência SQL local, superfície pública do agente e documentação da base.
- Affected behavior: quais transferências financeiras e emendas passam a ser carregadas automaticamente, quais campos ficam consultáveis e como o agente responde perguntas sobre esse domínio.
- Risk areas: mistura indevida com tabelas de receitas existentes, modelagem excessivamente genérica para duas fontes heterogêneas, deduplicação em reimportações e ambiguidade entre perguntas sobre transferências, receitas e despesas.
