## Context

O repositorio ja possui dois dominios proximos, mas com contratos diferentes:

- `despesa_documentos` guarda documentos executados de despesa, como empenhos, restos a pagar e documentos extras, com granularidade documental.
- `planejamento_despesas` guarda linhas mensais de planejamento orcamentario por orgao, unidade, programa e acao, vindas de XMLs dedicados.

O CSV em `data/xml/despesas/despesas-por-funcao/despesas-por-funcao-prefeitura-2025.csv` representa outra coisa: um relatorio agregado por funcao, com metadados de periodo e unidade gestora no cabecalho, varias linhas de ruido de exportacao (`="..."`) e uma linha sintetica de `Totais`. Hoje esse arquivo nao entra na base local nem na superficie publica do agente. Se o projeto tentar reaproveitar `planejamento_despesas` ou `despesa_documentos`, precisara inventar dimensoes que o arquivo nao fornece ou misturar dados agregados e documentais no mesmo contrato.

O pedido do usuario tambem exige uma nova tabela e tools SQL dedicadas. Portanto, a mudanca precisa cobrir ingestao, modelo/migration, tools publicas, roteamento/prompt e testes de regressao.

## Goals / Non-Goals

**Goals:**
- Incluir arquivos suportados de `despesas-por-funcao` no fluxo padrao de importacao local.
- Persistir os dados em uma tabela SQL dedicada, preservando metadados do relatorio e metricas monetarias por funcao.
- Garantir reimportacao idempotente e rastreavel para o relatorio.
- Expor o novo dominio ao agente por meio de tools publicas SQL de consulta e agregacao.
- Deixar explicita a fronteira entre esse relatorio agregado, `planejamento` e `despesas` documentais.

**Non-Goals:**
- Substituir `planejamento_despesas` como fonte para perguntas mensais por programa/acao.
- Reprocessar os XMLs genericos de `despesas` para popular o novo dominio.
- Criar dashboards ou UI dedicadas para o relatorio nesta mudanca.
- Generalizar desde ja qualquer outro relatorio agregado do portal com formato parecido.

## Decisions

### 1. Tratar `despesas-por-funcao` como um perfil de fonte CSV dedicado dentro da arvore de `despesas`

O pipeline deve reconhecer explicitamente os arquivos de `despesas-por-funcao` por padrao de pasta/nome e acionar um parser CSV dedicado, em vez de tentar encaixar o arquivo no parser XML de `despesas` ou no fluxo de `planejamentos`.

Rationale:
- O arquivo real e CSV, nao XML.
- O relatorio tem preambulo, cabecalho e rodape proprios, o que pede parsing especifico.
- A pasta ja esta operacionalmente dentro de `despesas`, entao faz sentido reaproveitar a descoberta do dominio sem misturar contratos de dados.

Alternatives considered:
- Reusar `PlanejamentosParser`: rejeitado porque o contrato de entrada e o schema de saida nao batem com o relatorio agregado.
- Tentar tratar o CSV como uma variante de `despesa_documentos`: rejeitado porque o arquivo nao representa documentos individuais.
- Criar um importador manual fora do pipeline: rejeitado porque quebraria o padrao usado no restante do projeto.

### 2. Criar uma tabela top-level dedicada chamada `despesas_por_funcao`

O armazenamento deve usar uma nova tabela, com colunas para linhagem de origem, metadados do relatorio e metricas por funcao. O contrato esperado inclui pelo menos `origem`, `exercicio`, `periodo_inicio`, `periodo_fim`, `unidade_gestora`, `funcao`, `dotacao_inicial`, `creditos_adicionais`, `dotacao_atualizada`, `valor_empenhado`, `valor_em_liquidacao`, `valor_liquidado` e `valor_pago`, alem de campos de auditoria como `arquivo_origem` e `linha_origem`.

Rationale:
- `planejamento_despesas` espera dimensoes mais granulares, como programa e acao, que esse CSV nao entrega.
- `despesa_documentos` modela documentos executados, nao relatorios agregados.
- Uma tabela dedicada evita campos nulos artificiais, semantica confusa e queries publicas ambivalentes.

Alternatives considered:
- Reusar `planejamento_despesas`: rejeitado porque exigiria popular dimensoes inexistentes e misturaria contratos de origem diferentes.
- Reusar `despesa_documentos`: rejeitado porque o arquivo nao tem identidade documental por empenho.
- Guardar so o CSV bruto sem normalizacao SQL: rejeitado porque impediria filtros e agregacoes auditaveis no padrao do projeto.

### 3. Extrair metadados do cabecalho e ignorar linhas sinteticas/ruido como registros de funcao

O parser deve ler as linhas iniciais do export para obter `exercicio`, `periodo`, `unidade_gestora` e validar o cabecalho de metricas. Depois disso, deve emitir apenas as linhas reais de funcao. Linhas como `Filtros Utilizados`, titulo do relatorio, `Totais` e carimbo final do sistema nao devem virar registros normais na tabela.

Rationale:
- O arquivo contem ruido estrutural que nao representa uma funcao consultavel.
- Importar a linha `Totais` como se fosse funcao causaria dupla contagem em agregacoes.
- O cabecalho contem metadados importantes que precisam ser propagados para cada linha persistida.

Alternatives considered:
- Importar a linha `Totais` com uma flag especial: rejeitado para v1 porque a soma SQL das funcoes ja produz o total sem risco de dupla contagem.
- Salvar todas as linhas do export exatamente como vieram: rejeitado porque isso reduziria a utilidade das tools publicas e aumentaria o ruido no contrato.

### 4. Usar uma chave de negocio estavel para idempotencia, mantendo linhagem de origem para auditoria

O contrato de reimportacao deve considerar que uma linha de `despesas-por-funcao` e identificada pela combinacao de `origem`, `exercicio`, `periodo_inicio`, `periodo_fim`, `unidade_gestora` e `funcao`. Campos como `arquivo_origem` e `linha_origem` devem ser preservados para rastreabilidade, mas a unicidade principal deve refletir a identidade do relatorio agregado.

Rationale:
- O arquivo ja entrega uma dimensao de negocio forte por periodo e funcao.
- Uma chave de negocio torna a reimportacao mais robusta do que depender so de linha fisica.
- A linhagem de origem ainda e util para auditoria e debugging.

Alternatives considered:
- Usar apenas `arquivo_origem + linha_origem`: rejeitado porque isso acopla demais a identidade a detalhes fisicos da exportacao.
- Deduplicar apenas por `funcao + exercicio`: rejeitado porque um mesmo ano pode ter mais de um periodo ou unidade gestora.

### 5. Expor o dominio com tools publicas dedicadas e fronteira clara contra `planejamento` e `despesas`

O agente deve ganhar tools como `consultar_despesas_por_funcao` e `agregar_despesas_por_funcao`, com filtros como `origem`, `ano`, `periodo`, `unidade_gestora`, `funcao` e faixas de valores. O roteamento e as docstrings devem deixar claro que esse dominio responde ao relatorio agregado por funcao, enquanto `planejamento` continua sendo a fonte para perguntas mensais por programa/acao e `despesas` continua sendo a fonte para documentos executados.

Rationale:
- O usuario nao deveria ter que conhecer a tabela ou abrir o CSV manualmente para consultar essas metricas.
- Tools dedicadas mantem auditabilidade e reduzem ambiguidade com dominios vizinhos.
- O pedido do usuario explicitamente inclui tools SQL e nova tabela.

Alternatives considered:
- Acrescentar mais filtros a `consultar_planejamento` e `agregar_planejamento`: rejeitado porque esconderia a diferenca entre as duas fontes.
- Expor o dominio apenas por SQL generico interno: rejeitado porque enfraquece o contrato publico do agente.

### 6. Exigir cobertura fim a fim com fixture representativa do relatorio real

A mudanca deve incluir testes de parser/schema, pipeline/persistencia e tools/roteamento, usando uma fixture que represente o layout real do CSV com cabecalho, linhas de funcao, `Totais` e carimbo final.

Rationale:
- O maior risco tecnico esta na normalizacao do export e na fronteira semantica com dominios existentes.
- Testar so a camada SQL ou so o parser nao prova que a mudanca ficou realmente usavel pelo agente.

Alternatives considered:
- Testar apenas insercao no banco com linhas fabricadas: rejeitado porque nao cobre o formato real do relatorio.
- Testar so o parser e confiar no restante da stack: rejeitado porque a integracao com tools e parte central do pedido.

## Risks / Trade-offs

- [Risk] Perguntas amplas como "quanto foi pago na saude?" podem competir com `planejamento` e com o novo dominio. -> Mitigation: documentar bem a fronteira nas docstrings, no prompt e nas regras de roteamento, priorizando o novo dominio quando a pergunta mirar explicitamente o relatorio por funcao.
- [Risk] O CSV exportado usa ruido visual, encoding e campos localizados que podem variar entre exercicios. -> Mitigation: centralizar leitura/normalizacao do CSV e cobrir o layout suportado com fixtures e falha previsivel para layouts desconhecidos.
- [Risk] Importar a linha `Totais` como registro normal pode causar dupla contagem. -> Mitigation: tratar essa linha como sintetica e nao persisti-la como `funcao`.
- [Risk] Novas variacoes do portal podem incluir mais granularidade do que o contrato v1 suporta. -> Mitigation: limitar a v1 ao perfil de arquivo validado hoje e tratar novas variantes como novos source profiles.

## Migration Plan

1. Adicionar o novo modelo SQL e a migration Alembic para `despesas_por_funcao`, com constraints e indices alinhados ao contrato publico.
2. Implementar parser/schema CSV para `despesas-por-funcao`, incluindo leitura de metadados do cabecalho e ignorando linhas sinteticas.
3. Integrar o novo perfil de arquivo ao pipeline e garantir upsert idempotente na tabela dedicada.
4. Criar as tools publicas de consulta e agregacao, registrando-as no conjunto publico do agente.
5. Atualizar prompt, roteamento compativel, documentacao e testes de regressao.

Rollback strategy:
- Remover o novo perfil de descoberta/importacao e esconder as tools publicas do dominio.
- Reverter a migration e o modelo dedicado caso o contrato do arquivo se mostre inadequado.

## Open Questions

- Perguntas amplas sobre `valor pago` por funcao devem preferir automaticamente o novo dominio mesmo sem a frase explicita `despesas por funcao`, ou apenas quando o recorte por funcao estiver claro?
- O contrato v1 deve preservar algum metadado textual adicional do cabecalho, como `apresentar por`, ou isso pode ficar fora enquanto o perfil suportado permanecer estavel?
