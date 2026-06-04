## Why

Hoje a tabela `servidores` mistura dois significados diferentes: ela guarda snapshots de folha usados pelas consultas publicas atuais, mas agora tambem precisa representar a relacao cadastral de servidores vinda de `relacao-servidores.json`. Manter esses dois contratos acoplados e ainda com relacionamento canonico entre `folha_servidores` e `servidores` aumenta ambiguidade, dificulta a migracao de formato e cria risco de o sistema continuar lendo os campos errados.

## What Changes

- Mover a semantica e os dados atuais de snapshot da tabela `servidores` para `folha_servidores`, tornando `folha_servidores` a origem dos campos usados hoje por folha e consultas publicas de salarios, cargos e setores.
- Remover o relacionamento e a logica canonica entre `folha_servidores` e `servidores`, incluindo foreign key, helpers de reconciliacao e usos ORM que assumem que uma tabela enriquece a outra.
- Redefinir a tabela `servidores` para armazenar exclusivamente a relacao de servidores importada de `data/xml/servidores/relacao-servidores/relacao-servidores.json`, mapeando todos os campos suportados do JSON e eliminando colunas herdadas do contrato antigo que nao se aplicam mais.
- Alterar a descoberta de arquivos, o parser `ServidoresParser`, o schema de ingestao e os testes do dominio `servidores` para ler JSON em vez de XML.
- Atualizar as tools e serializadores que hoje consultam `Servidor` para continuarem funcionando a partir de `folha_servidores` apos a separacao de contratos.

## Capabilities

### New Capabilities
- `folha-servidores-decoupled-snapshot-storage`: Define `folha_servidores` como persistencia desacoplada dos snapshots usados por folha e consultas publicas, sem dependencia da tabela `servidores`.
- `servidores-json-source-ingestion`: Define a descoberta, validacao e persistencia da nova fonte JSON de relacao de servidores na tabela `servidores`.
- `public-servidores-agent-access`: Define como as consultas publicas de servidores e os enriquecimentos de folha continuam acessando o contrato legado de snapshot apos a migracao para `folha_servidores`.

### Modified Capabilities
- None.

## Impact

- Affected code: `database/models/server.py`, `database/models/payroll.py`, migrations em `database/migrations/versions/`, `ingestion/pipeline.py`, `ingestion/parsers/xml/servidores_parser.py` ou eventual parser JSON equivalente, `ingestion/schemas/servidores.py`, SQL tools em `agents/tools/sql_tools/servidores/`, runtime de folha em `agents/tools/sql_tools/folha_pagamento/` e testes relacionados.
- Affected data: migracao com backfill dos registros atuais de `servidores`, remapeamento de referencias de `folha_pagamentos` e recriacao da tabela `servidores` com colunas novas.
- Affected behavior: a ingestao de `servidores` deixa de depender de XML, as consultas publicas de servidores passam a ler `folha_servidores`, e a tabela `servidores` deixa de representar snapshots salariais.
- Risk areas: perda de ligacao entre `folha_pagamentos` e snapshots migrados, divergencia entre colunas do JSON e schema SQL, e regressao nas tools publicas que hoje assumem `cargo`, `secretaria`, `salario_base` e `competencia_referencia` na model `Servidor`.
