## Context

O repositorio ja importa varios dominios administrativos e de transparencia para SQL local, com caminhos publicos para tools e roteamento do agente. Porem os XMLs de `estoques` em `data/xml/administracao/estoques/` ainda nao entram no fluxo normal de importacao nem possuem contrato SQL ou tools dedicadas.

O layout real de `estoques` e diferente dos dominios planos ja suportados:

- raiz `ESTOQUE`
- varios nos `MATERIAL`
- cada `MATERIAL` traz identificacao basica do item (`Material`, `UnidadeMedida`)
- um bloco `MOVIMENTACAOSUMARIZADA` com periodo, entradas, saidas e saldo
- zero ou mais linhas aninhadas em `MOVIMENTACAODIARIA/MOVIMENTACAODIARIA` com data, tipo de movimento, unidade gestora, almoxarifado, localizacao, classificacao, quantidade e valores

Como o pedido do usuario inclui ingestao, pipeline e tools, a mudanca cruza parser, persistencia, CLI, roteamento, documentacao e testes.

## Goals / Non-Goals

**Goals:**
- Incluir `estoques` no fluxo padrao de importacao local como um tipo de importacao dedicado.
- Persistir saldo sumarizado por material e historico diario de movimentacoes em contrato SQL proprio.
- Garantir reimportacao idempotente e rastreavel para materiais e movimentos.
- Expor tools publicas dedicadas para saldo de estoque, agregacoes sumarizadas e consulta de movimentacoes.
- Deixar clara a fronteira entre `estoques`, `patrimonios`, `despesas` e dominios de compras.

**Non-Goals:**
- Reconstruir fornecedores, licitacoes ou processos de compra a partir dos movimentos de estoque.
- Inferir centro de custo, destino final de consumo ou responsavel humano quando o XML nao trouxer esse dado.
- Criar dashboards, UI ou relatorios fora da superficie publica de tools e CLI.
- Resolver reconciliacao interanual ou consolidacao semantica entre arquivos `consolidada` e arquivos por origem alem do contrato minimo de importacao.

## Decisions

### 1. Tratar `estoques` como um tipo de importacao dedicado no fluxo padrao

O pipeline deve ganhar um novo tipo `estoques`, com descoberta explicita dos XMLs suportados sob `data/xml/administracao/estoques/estoque-*.xml`, atualizacao da ajuda do CLI e inclusao no conjunto default de importacao.

Rationale:
- O dominio nao pertence a `despesas`, `patrimonios` ou `frotas`; ele tem contrato proprio.
- Um tipo dedicado deixa a operacao mais audivel no relatorio de importacao e no `db status`.

Alternatives considered:
- Descobrir qualquer `*estoque*.xml`: rejeitado porque incluiria arquivos auxiliares ou vazios com risco de ruido silencioso.
- Encaixar `estoques` dentro de `patrimonios`: rejeitado porque patrimonio descreve bens cadastrados, nao saldo e movimentacao de almoxarifado.
- Tratar `estoques` como subtipo de `despesas`: rejeitado porque o XML descreve estoque e consumo, nao documentos orcamentarios.

### 2. Persistir o dominio em duas tabelas dedicadas: `estoque_materiais` e `estoque_movimentacoes`

O armazenamento deve usar um contrato pai-filho: uma tabela para o saldo sumarizado por material e outra para as movimentacoes diarias relacionadas. O registro de material deve guardar pelo menos `origem`, `arquivo_origem`, `sequencia_material`, `exercicio`, `material`, `unidade_medida`, `periodo_inicio`, `periodo_fim`, `saldo_anterior_quantidade`, `saldo_anterior_valor`, `entrada_quantidade`, `entrada_valor`, `saida_quantidade`, `saida_valor`, `saldo_quantidade` e `saldo_valor`. A tabela de movimentos deve guardar `material_id`, `sequencia_movimentacao`, `data_movimento`, `tipo_movimento`, `unidade_gestora`, `almoxarifado`, `localizacao`, `classificacao`, `quantidade`, `valor_unitario`, `valor_total` e `custo_medio`.

Rationale:
- O saldo sumarizado e o historico diario respondem perguntas diferentes e nao devem ser achatados no mesmo registro.
- Uma relacao pai-filho segue o padrao ja usado em dominios com detalhe aninhado, como `frota_veiculos` e `frota_despesas`.
- O contrato evita duplicar o saldo do material em cada linha de movimentacao e mantem as tools mais claras.

Alternatives considered:
- Tabela unica achatada por movimentacao com colunas de saldo repetidas: rejeitada por redundancia, ambiguidade e risco de agregacoes incorretas.
- Reusar `despesa_documentos`: rejeitado porque faltam identidade documental e semantica de estoque.
- Guardar apenas a movimentacao diaria e recalcular tudo em tempo de consulta: rejeitado porque materiais sem movimentos tambem precisam permanecer consultaveis.

### 3. Usar um loader customizado, modelado no fluxo de `frotas`, em vez do `SQLLoader` generico

O parser deve retornar materiais com lista aninhada de movimentos, e a persistencia deve passar por um metodo customizado no pipeline para upsert do material e substituicao controlada dos movimentos filhos quando a mesma linhagem for reimportada.

Rationale:
- O `SQLLoader` atual cobre melhor registros flat; aqui precisamos coordenar pai e filhos.
- O dominio precisa apagar e recriar movimentos da mesma linhagem quando o payload normalizado mudar, sem deixar filhos orfaos ou duplicados.
- O padrao de `frotas` ja prova que esse tipo de carregamento manual cabe na arquitetura atual.

Alternatives considered:
- Achatar movimentos e carregar tudo com batch generico: rejeitado porque perde a relacao explicita com o material pai e complica idempotencia.
- Persistir materiais e movimentos em duas passagens separadas sem coordenacao: rejeitado porque cria risco de inconsistencias parciais.

### 4. Definir idempotencia por linhagem de fonte, nao por chave de negocio natural

Como o XML nao fornece um identificador estavel de material ou de movimento, a unicidade deve se apoiar em `origem + arquivo_origem + sequencia_material` para o pai e `material_id + sequencia_movimentacao` para os filhos. Campos de negocio como descricao do material, unidade e periodo continuam indexados para consulta, mas nao viram a chave canonica de reimportacao.

Rationale:
- A amostra real ja mostra descricoes repetidas ou muito longas, o que torna chaves naturais frageis.
- O layout nao garante que almoxarifado ou classificacao existam no nivel sumarizado do material.
- A linhagem fisica do arquivo e deterministica e suficiente para v1.

Alternatives considered:
- Chave natural por `material + unidade_medida + periodo`: rejeitada porque o mesmo texto pode aparecer mais de uma vez e nao carrega toda a identidade da exportacao.
- Chave de movimento por `data + tipo + quantidade + valor_total`: rejeitada porque movimentos semelhantes podem se repetir legitimamente.

### 5. Expor tres tools publicas dedicadas e manter a fronteira semantica do dominio

O dominio publico deve nascer com:
- `consultar_estoques` para saldo sumarizado por material
- `agregar_estoques` para totais, contagens e rankings sobre metricas sumarizadas de entrada, saida e saldo
- `consultar_movimentacoes_de_estoque` para historico diario detalhado

As docstrings, o registro de tools e o roteamento devem deixar claro:
- `estoques` responde sobre materiais, saldos, entradas, saidas e historico de almoxarifado
- `patrimonios` continua cobrindo bens cadastrados
- `despesas` continua cobrindo documentos executados de gasto
- `licitacoes` e `contratos` continuam cobrindo compra e contratacao, nao a movimentacao posterior do item em estoque

Rationale:
- Saldo sumarizado e historico detalhado pedem formatos de resposta diferentes.
- Um par simples lookup/agregacao nao cobre bem perguntas de rastreio diario como requisicoes ou notas fiscais de compra de um material.
- Nomear o dominio explicitamente ajuda o agente a nao cair em tools vizinhas com semantica parecida.

Alternatives considered:
- Expor apenas `consultar_estoques` e `agregar_estoques`: rejeitado porque esconderia o historico diario, que e parte central do XML suportado.
- Reusar `consultar_patrimonios` para materiais: rejeitado porque patrimonio nao representa estoque consumivel.
- Responder via RAG ou leitura documental: rejeitado porque o pedido e por dado estruturado local e auditavel.

### 6. Cobertura fim a fim deve incluir fixture representativa com material sem movimento e material com multiplos movimentos

A suite precisa cobrir parser, pipeline/persistencia, registry/tools e roteamento. A fixture principal deve representar o layout real do XML: um material apenas sumarizado, outro com varias `MOVIMENTACAODIARIA`, diferentes tipos de movimento (`Nota Fiscal de Compra`, `Requisicao`, `Aplicacao Imediata`) e campos textuais relevantes como almoxarifado e classificacao.

Rationale:
- O maior risco esta na fronteira entre saldo e movimentacao, nao em um campo isolado.
- So testar parser ou so testar tools nao prova que o dominio ficou usavel pelo agente.

Alternatives considered:
- Testar apenas insercao no banco com linhas sinteticas: rejeitado porque nao valida o layout real da fonte.
- Cobrir apenas o saldo sumarizado: rejeitado porque deixaria o historico diario sem garantia.

## Risks / Trade-offs

- [Risk] XMLs de `estoques` podem ser volumosos e ter muitos movimentos por material. -> Mitigation: usar parser streaming-friendly dentro do padrao atual, fixture reduzida nos testes e loader transacional por material.
- [Risk] A chave por sequencia de origem depende da estabilidade do arquivo exportado. -> Mitigation: documentar explicitamente o contrato de linhagem v1 e reavaliar se surgir um identificador publico mais forte.
- [Risk] Perguntas como "material", "item" ou "compra" podem colidir com `patrimonios`, `despesas` ou `licitacoes`. -> Mitigation: reforcar palavras-guia, docstrings e rotas dedicadas para `estoques`, especialmente quando aparecerem termos como `almoxarifado`, `saldo`, `movimentacao`, `requisicao` ou `estoque`.
- [Risk] Algumas agregacoes por almoxarifado ou classificacao podem depender dos movimentos, nao do saldo sumarizado do material. -> Mitigation: manter a tool de movimentacoes separada e limitar a agregacao v1 ao contrato sumarizado suportado.

## Migration Plan

1. Adicionar os modelos SQLAlchemy e a migration Alembic para `estoque_materiais` e `estoque_movimentacoes`, com constraints e indices coerentes com o contrato publico.
2. Implementar parser/schema XML de `estoques`, incluindo normalizacao de periodo, valores decimais, origem do arquivo e lista aninhada de movimentos.
3. Integrar `estoques` ao CLI e ao `IngestionPipeline`, com descoberta explicita de arquivos e loader customizado para pai + filhos.
4. Criar as tools publicas dedicadas, registrando-as no conjunto publico do agente.
5. Atualizar roteamento, prompt/tool guidance, documentacao de banco/importacao e suites de teste.

Rollback strategy:
- Remover `estoques` do conjunto default de importacao e esconder as tools publicas do dominio.
- Reverter a migration e remover os modelos dedicados caso o contrato da fonte se prove inadequado.
- Voltar o roteamento para nao considerar `estoques` como dominio SQL suportado.

## Open Questions

- A tool de agregacao v1 deve operar apenas sobre o saldo sumarizado por material, ou vale incluir desde o inicio um modo explicito para agregacoes sobre movimentos diarios?
- O contrato publico deve expor a origem `consolidada` no mesmo nivel das origens `prefeitura`, `saude` e `camara`, ou convem trata-la inicialmente como um recorte mais cuidadoso para evitar dupla contagem em perguntas amplas?
- Materiais com descricao textual identica, mas repetidos em uma mesma exportacao, devem ser apresentados separadamente na resposta publica por padrao ou agrupados apenas quando o usuario pedir agregacao?
