## Why

O repositorio ja possui XMLs publicos de `estoques` em `data/xml/administracao/estoques/`, mas esse dominio ainda nao entra no fluxo normal de importacao nem pode ser consultado pelo agente por meio de tools SQL dedicadas. Isso deixa sem contrato local perguntas importantes sobre saldo de materiais, entradas, saidas, almoxarifados, classificacoes e historico de movimentacao do estoque municipal.

## What Changes

- Estender a ingestao local para descobrir os XMLs suportados de `estoques` e interpretar tanto o saldo sumarizado por material quanto as movimentacoes diarias aninhadas no arquivo.
- Persistir os dados importados em armazenamento SQL dedicado, preservando identidade da fonte, metadados do periodo, unidade gestora, almoxarifado, classificacao, quantidades e valores monetarios necessarios para consulta publica.
- Adicionar tools publicas de consulta e agregacao para `estoques`, incluindo suporte a perguntas sobre materiais, saldos, entradas, saidas e recortes por almoxarifado, classificacao ou periodo.
- Integrar o novo dominio ao registro publico de tools, ao roteamento e aos contratos de prompt para que perguntas estruturadas sobre estoque prefiram o caminho SQL dedicado.
- Cobrir o fluxo com testes de parser, persistencia, tools e roteamento, alem de atualizar a documentacao relevante da base e da importacao.

## Capabilities

### New Capabilities
- `estoques-source-ingestion`: Descobre XMLs suportados de `estoques`, normaliza materiais e movimentacoes diarias e persiste os dados em SQL com reimportacao idempotente.
- `public-estoques-agent-access`: Expoe os dados importados de `estoques` por meio de tools SQL publicas e integracao com o agente para consultas e agregacoes sobre saldo e movimentacao de materiais.

### Modified Capabilities
- None.

## Impact

- Affected code: `ingestion/pipeline.py`, novo parser/schema XML para `estoques`, `database/models/`, migrations em `database/migrations/versions/`, tools em `agents/tools/sql_tools/`, roteamento em `agents/routing/`, `docs/` e suites de teste relacionadas.
- Affected systems: descoberta de arquivos de ingestao, persistencia SQL local, registro publico de tools, roteamento do agente e documentacao operacional da base.
- Affected behavior: arquivos de `estoques` passam a ser carregados pela importacao local, os materiais e suas movimentacoes ficam consultaveis via SQL, e perguntas estruturadas sobre estoque deixam de depender de inferencia livre ou de fontes adjacentes.
- Risk areas: XML grande com registros aninhados, deduplicacao entre materiais e movimentacoes em reimportacoes, sobreposicao semantica com `patrimonios` e `despesas`, e definicao de um contrato publico que nao misture saldo sumarizado com historico detalhado sem clareza.
