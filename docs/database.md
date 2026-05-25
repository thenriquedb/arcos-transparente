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
- receitas
- servidores e folha de pagamento

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
```

---

## Tabelas

### `contratos`

Representa contratos administrativos importados do portal.

Campos principais:

- `numero`: número do contrato ou instrumento
- `fornecedor`: nome textual do fornecedor como veio da origem
- `cnpj`: documento textual do fornecedor
- `fornecedor_id`: vínculo opcional com a tabela `fornecedores`
- `valor`
- `data_inicio`
- `data_fim`
- `categoria`
- `secretaria`
- `descricao`

Regras importantes:

- unicidade por `numero + data_inicio`
- índice composto para consultas por `secretaria + categoria + data_inicio`

Observação:

Mesmo mantendo `fornecedor` e `cnpj` textuais por rastreabilidade, a coluna `fornecedor_id`
permite consultas transversais com licitações e outros domínios.

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
- analisar custos de frota:
  cruzar `frota_veiculos` e `frota_despesas`

---

## Arquivos Relacionados

- modelos ORM: `database/models/`
- sessão SQLAlchemy: `database/session.py`
- migrations: `database/migrations/versions/`
- pipeline de carga: `ingestion/pipeline.py`
- documentação operacional: `docs/importacao.md`
