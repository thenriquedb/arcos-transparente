## 1. Restructurar persistencia e migracao de dados

- [x] 1.1 Criar uma migration Alembic que mova o contrato legado de snapshot para `folha_servidores`, incluindo colunas, indices e backfill dos dados hoje armazenados em `servidores`.
- [x] 1.2 Remapear `folha_pagamentos.servidor_id` para os snapshots migrados, remover a foreign key e a coluna canonica que ligam `folha_servidores` a `servidores`, e recriar a tabela `servidores` com o novo contrato JSON.
- [x] 1.3 Atualizar as models SQLAlchemy de `Servidor`, `FolhaServidor` e exports relacionados para refletir a nova semantica das duas tabelas.

## 2. Atualizar ingestao de servidores e manutencao de folha

- [x] 2.1 Alterar a descoberta de arquivos do dominio `servidores` para reconhecer `relacao-servidores.json` como fonte suportada e parar de tratar o dominio como parser XML de folha.
- [x] 2.2 Adaptar `ServidoresParser` e `ServidorInSchema` para ler JSON, normalizar todos os campos suportados do novo arquivo e persisti-los de forma idempotente na nova tabela `servidores`.
- [x] 2.3 Ajustar a carga de `folha_pagamento` para resolver ou criar snapshots em `folha_servidores` sem usar reconciliacao com a tabela `servidores`.

## 3. Preservar comportamento das tools publicas

- [x] 3.1 Migrar `consultar_servidores`, `agregar_servidores` e seus helpers compartilhados para usar `folha_servidores` como fonte do contrato legado de salarios, cargos, secretarias e mes de referencia.
- [x] 3.2 Atualizar os serializadores e fluxos de `buscar_historico_de_pagamentos_do_servidor` para remover a dependencia de `FolhaServidor.servidor_canonico`.

## 4. Validar parser, migracao e regressao funcional

- [x] 4.1 Atualizar ou adicionar testes de parser e schema para o novo JSON de `servidores`, cobrindo datas, campos vazios, obrigatorios e reimportacao.
- [x] 4.2 Atualizar testes de pipeline, migracao e tools publicas para cobrir o backfill de `folha_servidores`, o remapeamento de `folha_pagamentos` e a continuidade das consultas publicas.
- [x] 4.3 Executar a bateria relevante de testes e validar manualmente uma importacao do JSON novo e uma consulta representativa de folha/servidores no banco local.
