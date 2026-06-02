## ADDED Requirements

### Requirement: Homepage inicial apresenta o serviço em linguagem cidadã
The system MUST exibir, na tela inicial do chat e em português do Brasil, um resumo breve que explique que o Arcos Transparente ajuda a consultar dados públicos municipais e informações institucionais úteis da cidade sem exigir conhecimento técnico.

#### Scenario: Resumo aparece antes da primeira pergunta
- **WHEN** a pessoa abre a homepage e ainda não enviou nenhuma mensagem
- **THEN** a interface mostra um resumo curto do serviço em linguagem simples
- **AND** o texto evita jargões técnicos e administrativos desnecessários

#### Scenario: Conversa ativa reduz o destaque do conteúdo introdutório
- **WHEN** a sessão já possui pelo menos uma mensagem enviada
- **THEN** a interface prioriza o histórico da conversa e o campo de pergunta
- **AND** o conteúdo inicial deixa de competir visualmente com a interação principal

### Requirement: Homepage inicial oferece perguntas de exemplo acionáveis
The system MUST mostrar perguntas de exemplo em português do Brasil, escritas como perguntas reais de cidadãos e cobrindo mais de um domínio importante do produto.

#### Scenario: Exemplos cobrem consultas frequentes
- **WHEN** a homepage é exibida no estado inicial
- **THEN** a interface apresenta exemplos que incluam pelo menos consultas sobre gastos, salários, contratos ou licitações, receitas ou orçamento, e informações úteis da cidade
- **AND** os exemplos usam vocabulário cotidiano em vez de linguagem técnica

#### Scenario: Clique em exemplo acelera o início da conversa
- **WHEN** a pessoa seleciona uma das perguntas de exemplo
- **THEN** a interface usa o texto da pergunta escolhida como entrada da conversa
- **AND** o fluxo reduz o esforço necessário para começar a consultar

### Requirement: Campo de pergunta orienta o uso com placeholder acessível
The system MUST usar um placeholder em português do Brasil que ajude a pessoa a entender rapidamente quais tipos de assunto podem ser consultados.

#### Scenario: Placeholder explicita temas aceitos
- **WHEN** o campo de pergunta é exibido sem texto digitado
- **THEN** o placeholder menciona exemplos de temas compatíveis com o escopo do sistema, como salários, contratos, receitas, diárias, passagens ou telefones úteis
- **AND** a frase permanece curta o suficiente para ser lida de imediato

### Requirement: Homepage informa o que está disponível para consulta
The system MUST mostrar, na tela inicial, um resumo do que pode ser consultado, separado em grupos compreensíveis para o público geral.

#### Scenario: Dados estruturados e informações institucionais aparecem como grupos distintos
- **WHEN** a pessoa visualiza a seção sobre dados disponíveis
- **THEN** a interface separa conteúdos de transparência, como despesas, contratos, licitações, servidores, receitas, patrimônio e frota, de conteúdos de orientação pública, como telefones úteis, horários de ônibus, estrutura organizacional e perguntas frequentes
- **AND** essa distinção é feita sem usar termos internos de arquitetura do sistema

### Requirement: Homepage divulga origem dos dados e faixa temporal disponível
The system MUST informar de forma visível, na homepage inicial, de onde vêm os dados apresentados pelo sistema e qual é a faixa temporal geral disponível para consulta.

#### Scenario: Origem dos dados é explicada em linguagem simples
- **WHEN** a pessoa consulta a seção sobre origem dos dados
- **THEN** a interface informa que o sistema reúne dados públicos e conteúdos institucionais locais derivados de fontes públicas do município, incluindo prefeitura, câmara e acervo municipal curado do projeto
- **AND** o texto evita detalhes técnicos sobre importação, banco de dados ou arquitetura

#### Scenario: Faixa temporal geral é exibida com ressalva de cobertura
- **WHEN** a pessoa consulta a informação de período da base
- **THEN** a homepage mostra a faixa geral `2025 a maio de 2026`
- **AND** a interface informa que alguns assuntos podem ter cobertura diferente conforme os arquivos disponíveis na base local

### Requirement: Homepage deixa limites e expectativas claros
The system MUST incluir um aviso curto sobre os limites da base para reduzir interpretações erradas antes da primeira consulta.

#### Scenario: Aviso prepara a pessoa para ausência de dados
- **WHEN** a homepage inicial é exibida
- **THEN** a interface informa que as respostas dependem dos dados já disponíveis na base local
- **AND** deixa claro que pode haver temas sem registros ou com cobertura parcial
