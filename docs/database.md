# Estrutura do Banco de Dados

## Visão Geral

O banco do Observatório Arcos usa SQLite com SQLAlchemy ORM e migrations via Alembic.
O objetivo da modelagem é equilibrar:

- rastreabilidade dos dados importados
- integridade relacional
- boa performance para filtros e agregações
- compatibilidade com consultas analíticas e tools para LLM

O schema está dividido em domínios:

- contratos
- licitações
- fornecedores
- frotas
- estoques
- receitas
- transferências financeiras
- servidores e folha de pagamento
- planejamento de despesas
- documentos de despesa
- patrimônios
- quadro de pessoal

---

## Convenções Gerais

Quase todas as tabelas seguem o mesmo padrão:

- `id`: chave primária inteira autoincremental
- `criado_em`: data/hora de criação do registro
- `atualizado_em`: data/hora da última atualização

Outras decisões importantes:

- valores monetários usam `Numeric(15, 2)` ou `Numeric(15, 4)` quando há necessidade de mais precisão
- datas usam `Date`
- duplicidade é controlada por `UniqueConstraint`
- relacionamentos usam `ForeignKey`
- filtros frequentes recebem índices simples ou compostos

---

## Mapa Geral

```text
fornecedores
├── contratos
├── vencedores_licitacao
└── instrumentos_contratuais

licitacoes
├── vencedores_licitacao
└── instrumentos_contratuais
    └── materias_instrumento

servidores
└── folha_servidores
    └── folha_pagamentos
        ├── folha_cargos
        └── folha_lotacoes

receita_naturezas
└── receita_arrecadacoes

frota_veiculos
└── frota_despesas

estoque_materiais
└── estoque_movimentacoes

transferencias_financeiras_movimentos

emendas_parlamentares

planejamento_despesas

despesas_por_funcao

despesa_documentos
├── despesa_documento_itens
└── despesa_documentos_comprobatorios

patrimonios

quadro_pessoal
```

---

## Tabelas

### `contratos`

Representa contratos administrativos importados do portal.

Campos principais:

- `numero`: número do contrato ou instrumento
- `numero_licitatorio`: número da licitação de origem, quando existir
- `numero_instrumento`: número específico do instrumento contratual
- `tipo_instrumento_contratual`
- `fornecedor`: nome textual do fornecedor como veio da origem
- `cnpj`: documento textual do fornecedor
- `fornecedor_id`: vínculo opcional com a tabela `fornecedores`
- `valor`
- `data_inicio`
- `data_fim`
- `categoria`
- `secretaria`
- `possui_aditivo`
- `descricao`
- `descricao_despesa`: resumo textual das classificações orçamentárias associadas
- `xml_original`: XML bruto do `InstrumentoContratual` importado, preservado para auditoria

Regras importantes:

- unicidade por `numero + data_inicio`
- índice composto para consultas por `secretaria + categoria + data_inicio`
- índice composto para `numero_licitatorio + data_inicio`

Observação:

Mesmo mantendo `fornecedor` e `cnpj` textuais por rastreabilidade, a coluna `fornecedor_id`
permite consultas transversais com licitações e outros domínios.

O domínio de contratos também mantém tabelas filhas para preservar a granularidade do XML
sem achatar a informação em uma única coluna.

### `contrato_despesas_orcamentarias`

Detalha as despesas orçamentárias vinculadas a cada contrato.

Campos principais:

- `contrato_id`
- `ordem`: posição original do item no XML
- `unidade_gestora`
- `exercicio`
- `orgao`
- `unidade`
- `departamento`
- `fonte_recurso`
- `natureza_despesa_rubrica`
- `descricao_despesa`
- `valor_despesa`

Relacionamentos:

- pertence a um `contrato`

### `contrato_itens_adquiridos`

Detalha os itens adquiridos vinculados a cada contrato.

Campos principais:

- `contrato_id`
- `ordem`: posição original do item no XML
- `unidade_gestora`
- `numero_lote`
- `numero_item`
- `identificacao`
- `quantidade`
- `valor_unitario`
- `valor_total`

Relacionamentos:

- pertence a um `contrato`

### `fornecedores`

Cadastro canônico de fornecedores.

Campos principais:

- `cnpj_cpf`
- `nome`

Relacionamentos:

- um fornecedor pode aparecer em vários `contratos`
- um fornecedor pode aparecer em vários `vencedores_licitacao`
- um fornecedor pode aparecer em vários `instrumentos_contratuais`

Regras importantes:

- unicidade por `cnpj_cpf + nome`

### `licitacoes`

Tabela principal das licitações.

Campos principais:

- `numero`
- `modalidade`
- `objeto`
- `valor_estimado`
- `data_abertura`
- `situacao`
- `secretaria`

Relacionamentos:

- uma licitação tem vários `vencedores_licitacao`
- uma licitação tem vários `instrumentos_contratuais`

Regras importantes:

- unicidade por `numero + data_abertura`
- índice composto para `secretaria + situacao + data_abertura`

### `vencedores_licitacao`

Representa os vencedores associados a cada licitação.

Campos principais:

- `licitacao_id`
- `fornecedor_id`
- `cnpj_cpf`
- `nome`
- `validade_proposta`

Relacionamentos:

- pertence a uma `licitacao`
- pode apontar para um `fornecedor`

Regras importantes:

- unicidade por `licitacao_id + cnpj_cpf + nome`

### `instrumentos_contratuais`

Representa contratos, atas e outros instrumentos gerados a partir de uma licitação.

Campos principais:

- `licitacao_id`
- `fornecedor_id`
- `numero_licitatorio`
- `unidade_gestora`
- `tipo_instrumento_contratual`
- `numero_instrumento`
- `tipo_contrato`
- `objeto`
- `data_emissao`
- `data_expiracao`
- `possui_aditivo`
- `valor_instrumento_contratual`

Relacionamentos:

- pertence a uma `licitacao`
- pode apontar para um `fornecedor`
- possui várias `materias_instrumento`

Regras importantes:

- unicidade por `licitacao_id + numero_instrumento`
- índice composto por `fornecedor_id + data_emissao`

### `materias_instrumento`

Detalha os itens, lotes e materiais de cada instrumento contratual.

Campos principais:

- `instrumento_id`
- `unidade_gestora`
- `numero_lote`
- `numero_item`
- `identificacao`
- `quantidade`
- `valor_unitario`
- `valor_total`

Relacionamentos:

- pertence a um `instrumentos_contratuais`

Regras importantes:

- unicidade por `instrumento_id + numero_lote + numero_item`

### `servidores`

Snapshots mensais de servidores derivados da folha de pagamento.

Campos principais:

- `nome`
- `cargo`
- `secretaria`
- `salario_base`
- `competencia_referencia`

Relacionamentos:

- um servidor pode estar vinculado a vários registros de `folha_servidores`

Regras importantes:

- unicidade por `nome + cargo + secretaria + competencia_referencia`
- índice composto por `secretaria + cargo + competencia_referencia`

Observação:

Esta tabela não contém data de admissão. O portal de origem só expõe a competência
mensal do pagamento, então o recorte temporal armazenado aqui é a competência
de referência do registro.

### `folha_servidores`

Dimensão de nomes de servidores usada na folha de pagamento.

Campos principais:

- `nome`
- `servidor_id`: vínculo opcional com `servidores`

Relacionamentos:

- um `folha_servidores` possui vários `folha_pagamentos`
- pode apontar para um `servidores`

Objetivo:

Separar o identificador usado pela folha da entidade canônica de servidor, permitindo reconciliação gradual.

### `folha_cargos`

Dimensão textual de cargos da folha.

Campos principais:

- `nome`

Relacionamentos:

- um cargo pode aparecer em vários `folha_pagamentos`

### `folha_lotacoes`

Dimensão textual de lotações da folha.

Campos principais:

- `nome`

Relacionamentos:

- uma lotação pode aparecer em vários `folha_pagamentos`

### `folha_pagamentos`

Fato mensal da folha de pagamento.

Campos principais:

- `competencia_ano`
- `competencia_mes_num`
- `competencia_mes_nome`
- `servidor_id`
- `lotacao_id`
- `cargo_id`
- `salario_base`
- `proventos`
- `vantagens`
- `vencimentos_totais`
- `descontos`
- `liquido`

Relacionamentos:

- pertence a `folha_servidores`
- pode apontar para `folha_lotacoes`
- pode apontar para `folha_cargos`

Regras importantes:

- unicidade por `competencia_ano + competencia_mes_nome + servidor_id + cargo_id + lotacao_id`
- índice composto por `competencia_ano + competencia_mes_num + lotacao_id`
- índice composto por `competencia_ano + competencia_mes_num + servidor_id`

Observação:

Essa tabela é a principal fonte para perguntas como:

- quanto um servidor recebeu em determinado mês
- quais cargos receberam mais em um período
- qual lotação teve maior massa salarial

### `receita_naturezas`

Dimensão de classificação de receitas.

Campos principais:

- `identificacao`
- `nome`
- `nivel`
- `identificacao_superior`

Relacionamentos:

- uma natureza pode estar associada a várias `receita_arrecadacoes`

Objetivo:

Permitir análise por categoria de receita e futura navegação hierárquica por níveis.

### `receita_arrecadacoes`

Fato de arrecadação de receitas.

Campos principais:

- `exercicio`
- `mes`
- `data_arrecadacao`
- `unidade_gestora`
- `natureza_id`
- `fonte_recurso`
- `valor_previsto_bruto`
- `valor_arrecadado_bruto`
- `valor_previsto_deducoes`
- `valor_realizado_deducoes`
- `valor_previsto_liquido`
- `valor_arrecadado_liquido`

Relacionamentos:

- pode apontar para `receita_naturezas`

Regras importantes:

- unicidade por `data_arrecadacao + unidade_gestora + natureza_id + fonte_recurso`
- índice composto por `exercicio + mes + natureza_id + unidade_gestora`

### `receita_lancamentos`

Fato de lançamentos tributários.

Campos principais:

- `exercicio`
- `mes`
- `data_lancamento`
- `tipo_receita`
- `tributo`
- `valor_lancado_exercicio`
- `valor_lancado_divida_ativa`
- `valor_lancado_cobraca_judicial`

Regras importantes:

- unicidade por `data_lancamento + tipo_receita + tributo + valor_lancado_exercicio`
- índice composto por `exercicio + mes + tipo_receita + tributo`

Observação:

Embora faça parte do domínio de receitas, essa tabela não representa arrecadação efetiva,
mas sim valores lançados.

### `transferencias_financeiras_movimentos`

Movimentos financeiros entre unidades públicas, como repasses, recebimentos e devoluções.

Campos principais:

- `arquivo_origem`
- `sequencia_origem`
- `exercicio`
- `identificacao`
- `unidade_gestora_concessora`
- `unidade_gestora_recebedora`
- `finalidade`
- `fonte_recurso`
- `detalhamento_fonte`
- `programacao_inicial`
- `data_movimento`
- `tipo_movimento`
- `valor_movimento`

Regras importantes:

- unicidade por `arquivo_origem + sequencia_origem`
- índices por `exercicio`, `data_movimento`, `identificacao`, `tipo_movimento`, `unidade_gestora_concessora` e `unidade_gestora_recebedora`

Observação:

Essa tabela preserva a semântica própria do domínio de transferências financeiras, sem
coagir os movimentos para as tabelas de receitas ou despesas.

### `emendas_parlamentares`

Emendas parlamentares importadas de relatórios CSV do portal.

Campos principais:

- `arquivo_origem`
- `sequencia_origem`
- `exercicio_consulta`
- `ano`
- `ano_numero`
- `autor`
- `objeto`
- `tipo_emenda`
- `funcao`
- `valor`

Regras importantes:

- unicidade por `arquivo_origem + sequencia_origem`
- índices por `ano`, `ano_numero`, `autor`, `exercicio_consulta`, `funcao` e `tipo_emenda`

Observação:

`exercicio_consulta` preserva o exercício do relatório exportado, enquanto `ano`
representa o ano embutido no identificador `ano_numero`, útil para filtros públicos.

### `frota_veiculos`

Cadastro de veículos e bens de frota.

Campos principais:

- `codigo_veiculo`
- `placa_patrimonio`
- `placa_veiculo`
- `descricao_material`
- `unidade_gestora`
- `tipo_veiculo`
- `marca`
- `modelo`
- `data_aquisicao`
- `localizacao`
- `descricao`
- `ano_fabricacao`
- `situacao_veiculo`
- `situacao_veiculo_patrimonio`
- `estado_conservacao`
- `renavam`
- `chassi`
- `ano_modelo`
- `qtd_passageiros`
- `marcador_atual`
- `unidade_medida`
- `fornecedor`
- `cor_predominante`
- `valor_atual`

Relacionamentos:

- um veículo possui várias `frota_despesas`

Regras importantes:

- unicidade por `codigo_veiculo + placa_veiculo`

### `frota_despesas`

Despesas e eventos associados aos veículos.

Campos principais:

- `veiculo_id`
- `descricao_evento`
- `quantidade_lancamento`
- `valor_lancamento`
- `data_evento`
- `tp_despesa`
- `tipo_despesa`
- `total_despesa`

Relacionamentos:

- pertence a `frota_veiculos`

Regras importantes:

- unicidade por `veiculo_id + descricao_evento + data_evento + valor_lancamento`

### `planejamento_despesas`

Linhas mensais do planejamento e execução orçamentária da despesa.

Campos principais:

- `origem`: recorte do arquivo importado, como `saude` ou `prefeitura`
- `exercicio`
- `mes` e `mes_num`
- `unidade_gestora`, `orgao`, `unidade`
- `funcao`, exposta nas tools como `area`
- `subfuncao`, exposta nas tools como `subarea`
- `programa`
- `descricao_acao`, exposta nas tools como `acao`
- `fonte_recurso_identificacao` e `fonte_recurso_descricao`
- `categoria_economica_*`, `grupo_despesa_*`, `elemento_despesa_*`
- `dotacao_inicial`, exposta como `orcamento_inicial`
- `dotacao_atualizada`, exposta como `orcamento_atualizado`
- `valor_empenhado`, exposto como `valor_comprometido`
- `valor_liquidado`, exposto como `valor_confirmado`
- `valor_pago`
- `valor_anulado`, exposto como `valor_cancelado`

Regras importantes:

- unicidade por origem, ano, mês e principais dimensões orçamentárias
- filtros textuais nas tools ignoram diferenças de acento
- importa os arquivos de planejamento da saúde e da prefeitura

### `estoque_materiais`

Saldos sumarizados de materiais importados dos XMLs de estoque.

Campos principais:

- `arquivo_origem` e `sequencia_material`: preservam a linhagem do material no XML
- `origem`, `exercicio`
- `material`, `unidade_medida`
- `periodo_inicio` e `periodo_fim`
- `saldo_anterior_quantidade`, `saldo_anterior_valor`
- `entrada_quantidade`, `entrada_valor`
- `saida_quantidade`, `saida_valor`
- `saldo_quantidade`, `saldo_valor`

Relacionamentos:

- possui varias `estoque_movimentacoes`

Regras importantes:

- unicidade por `origem + arquivo_origem + sequencia_material`
- materiais sem historico diario continuam persistidos no contrato sumarizado
- esse contrato representa saldo e fluxo de almoxarifado, nao patrimonio, documento de despesa ou processo de compra

### `estoque_movimentacoes`

Historico diario de movimentacoes vinculado a um material de estoque.

Campos principais:

- `material_id`
- `sequencia_movimentacao`
- `data_movimento`
- `tipo_movimento`
- `unidade_gestora`
- `almoxarifado`
- `localizacao`
- `classificacao`
- `quantidade`
- `valor_unitario`
- `valor_total`
- `custo_medio`

Relacionamentos:

- pertence a `estoque_materiais`

Regras importantes:

- unicidade por `material_id + sequencia_movimentacao`
- a tabela guarda apenas movimentacoes realmente presentes no XML; nao inventa detalhes para materiais apenas sumarizados

### `despesas_por_funcao`

Linhas agregadas do relatório CSV `despesas-por-funcao`.

Campos principais:

- `arquivo_origem` e `linha_origem`: preservam a linhagem do CSV importado
- `origem`, `exercicio`
- `periodo_inicio` e `periodo_fim`
- `unidade_gestora`
- `funcao`
- `dotacao_inicial`
- `creditos_adicionais`
- `dotacao_atualizada`
- `valor_empenhado`
- `valor_em_liquidacao`
- `valor_liquidado`
- `valor_pago`

Regras importantes:

- unicidade por origem, exercício, período, unidade gestora e função
- a linha sintética `Totais` do relatório não é persistida para evitar dupla contagem
- esse contrato é diferente de `planejamento_despesas`: aqui a granularidade é o relatório agregado por função, não linhas mensais por programa/ação

### `despesa_documentos`

Documentos de despesa importados de empenhos, restos a pagar e documentos extras.

Campos principais:

- `tipo_origem`: `empenho`, `restos_a_pagar` ou `documento_extra`
- `arquivo_origem` e `sequencia_origem`: preservam a linha original do XML
- `origem`, `exercicio`, `unidade_gestora`
- classificações orçamentárias (`funcao`, `subfuncao`, `programa`, fonte, categoria, grupo, elemento)
- `conta_extra_*` para documentos extraorçamentários
- `numero_documento`, `data_documento`, `credor`, `cpf_cnpj`
- `valor_documento`, `valor_empenhado`, `valor_liquidado`, `valor_pago`, `valor_anulado`
- campos de diária/viagem quando presentes

Relacionamentos:

- possui vários `despesa_documento_itens`
- possui vários `despesa_documentos_comprobatorios`

### `patrimonios`

Bens patrimoniais importados dos XMLs de administração.

Campos principais:

- `unidade_gestora`, `placa`, `situacao_bem`, `classificacao`
- `descricao_item`, `tipo_ingresso`, `data_aquisicao`, `data_baixa`
- `localizacao`, `status`
- `valor_ingresso`, `valor_atualizado`

### `quadro_pessoal`

Totais mensais de vagas por regime de contratação.

Campos principais:

- `origem`
- `competencia_referencia`
- `regime_contratacao`
- `vagas_criadas`
- `vagas_preenchidas`

---

## Relacionamentos Mais Importantes

Os relacionamentos abaixo são os mais úteis para queries e tools:

- `fornecedores -> contratos`
- `fornecedores -> vencedores_licitacao`
- `fornecedores -> instrumentos_contratuais`
- `licitacoes -> vencedores_licitacao`
- `licitacoes -> instrumentos_contratuais -> materias_instrumento`
- `servidores -> folha_servidores -> folha_pagamentos`
- `folha_cargos -> folha_pagamentos`
- `folha_lotacoes -> folha_pagamentos`
- `receita_naturezas -> receita_arrecadacoes`
- `frota_veiculos -> frota_despesas`
- `estoque_materiais -> estoque_movimentacoes`
- `transferencias_financeiras_movimentos`
- `emendas_parlamentares`
- `despesa_documentos -> despesa_documento_itens`
- `despesa_documentos -> despesa_documentos_comprobatorios`

---

## Como Pensar as Consultas

### Consultas por fornecedor

Para cruzar participação de empresa em contratos e licitações, o caminho preferencial é:

- `fornecedores`
- `contratos`
- `vencedores_licitacao`
- `instrumentos_contratuais`

### Consultas por servidor

Para perguntas de folha e histórico funcional:

- use `folha_pagamentos` para valores mensais
- use `folha_servidores` para localizar o nome na folha
- use `servidores` quando precisar de cargo, secretaria e salário-base por competência

### Consultas por receita

Há dois tipos de pergunta diferentes:

- arrecadação efetiva: `receita_arrecadacoes`
- valores lançados: `receita_lancamentos`

### Consultas por transferências financeiras

Para perguntas sobre repasses à Câmara, recebimentos, devoluções ou emendas parlamentares:

- use `transferencias_financeiras_movimentos` para movimentações entre unidades públicas
- use `emendas_parlamentares` para valores destinados por autor, função ou tipo de emenda

### Consultas por licitação

Perguntas sobre resultado e detalhamento geralmente exigem join entre:

- `licitacoes`
- `vencedores_licitacao`
- `instrumentos_contratuais`
- `materias_instrumento`

---

## Cuidados e Limitações Atuais

- algumas chaves únicas incluem campos opcionais; no SQLite, valores `NULL` em constraints únicas exigem cuidado em reimportações
- `receita_naturezas` ainda usa `identificacao_superior` textual, sem relação hierárquica explícita
- a reconciliação entre `folha_servidores` e `servidores` é progressiva e depende da qualidade do dado de origem
- `contratos` mantém tanto o texto original do fornecedor quanto a referência canônica por `fornecedor_id`

---

## Recomendações para Tools de LLM

Para a arquitetura atual do agente, superfícies públicas reduzidas e estratégia de roteamento,
consulte também: [docs/arquitetura-agent-tools.md](./arquitetura-agent-tools.md)

Ao criar tools, vale pensar em contratos de entrada e saída que respeitem a estrutura do banco:

- buscar servidor por nome:
  consultar `folha_servidores`, depois enriquecer com `folha_pagamentos` e `servidores`
- buscar fornecedor por documento:
  partir de `fornecedores` e cruzar contratos e licitações
- detalhar licitação:
  usar `consultar_licitacoes` com `incluir_detalhes=True` para expandir vencedores, instrumentos e matérias
- resumir receita por período:
  usar `receita_arrecadacoes` com filtros por `exercicio`, `mes`, `unidade_gestora` e `natureza_id`
- consultar repasses e emendas:
  usar `consultar_transferencias_financeiras` ou `agregar_transferencias_financeiras`
- consultar o relatório agregado por função:
  usar `consultar_despesas_por_funcao` ou `agregar_despesas_por_funcao`
- consultar saldo e historico de estoque:
  usar `consultar_estoques`, `agregar_estoques` e `consultar_movimentacoes_de_estoque`
- analisar custos de frota:
  cruzar `frota_veiculos` e `frota_despesas`

---

## Arquivos Relacionados

- modelos ORM: `database/models/`
- sessão SQLAlchemy: `database/session.py`
- migrations: `database/migrations/versions/`
- pipeline de carga: `ingestion/pipeline.py`
- documentação operacional: `docs/importacao.md`
