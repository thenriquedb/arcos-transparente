## Context

A interface atual do Arcos Transparente em `agents/chatbot/web.py` mostra apenas o título, uma legenda curta e o campo de chat. Existe uma função de sugestões de perguntas no código, mas ela está desativada e ainda usa exemplos mais genéricos do que o produto hoje suporta. Ao mesmo tempo, o prompt do agente já deixa claro que o público é composto por cidadãos comuns e que o sistema cobre tanto dados estruturados de transparência quanto um pequeno acervo local de informações institucionais.

Essa combinação gera um problema de produto simples, mas importante: a pessoa chega a uma tela vazia, não entende o que pode perguntar, não sabe de onde vêm os dados e não consegue perceber os limites da base. A homepage precisa preencher essa lacuna sem exigir conhecimento técnico, sem usar jargão administrativo e sem competir com a experiência principal de conversa.

Há também uma restrição de consistência: a homepage deve refletir o escopo real do chatbot, incluindo domínios como diárias, passagens, eleitos, telefones úteis e horários de ônibus, mas sem prometer cobertura total para qualquer período. O texto inicial precisa deixar visível que a faixa temporal exibida na primeira versão será `2025 a maio de 2026`, com um aviso curto de que a disponibilidade pode variar conforme o tema e os arquivos já carregados na base local.

## Goals / Non-Goals

**Goals:**
- Transformar a homepage vazia em uma tela inicial de orientação cidadã, em português do Brasil e com linguagem cotidiana.
- Explicar de forma rápida o que o sistema faz, o que pode ser consultado e como começar.
- Exibir perguntas de exemplo acionáveis cobrindo os principais tipos de consulta.
- Tornar visíveis a origem dos dados e a faixa temporal da base, com texto simples e sem excesso de detalhe técnico.
- Preservar o chat como foco principal da interface após o início da conversa.

**Non-Goals:**
- Redesenhar toda a identidade visual do app ou migrar a interface para outra tecnologia.
- Alterar o comportamento do agente, das tools SQL ou do fluxo RAG.
- Criar detecção automática da faixa temporal diretamente do banco nesta mudança.
- Resolver inconsistências documentais antigas fora do escopo da homepage.

## Decisions

### 1. Tratar a homepage como estado inicial da conversa

O novo conteúdo deve aparecer com destaque apenas quando a sessão ainda não tiver mensagens. Depois da primeira pergunta, a interface volta a priorizar o histórico da conversa e o campo de entrada.

Rationale:
- A maior necessidade de orientação acontece no primeiro contato.
- Isso evita repetir textos longos em toda mensagem e preserva a leveza do chat.

Alternatives considered:
- Manter o conteúdo sempre visível acima do histórico: rejeitado porque polui a conversa em sessões longas.
- Mover toda a orientação para uma sidebar: rejeitado porque reduz descoberta em telas menores e enfraquece a mensagem principal.

### 2. Organizar o conteúdo inicial em blocos curtos e legíveis

A homepage deve agrupar a orientação em poucos blocos com títulos claros, por exemplo:
- resumo do serviço
- perguntas de exemplo
- o que você pode consultar
- de onde vêm os dados
- período disponível e limites da base

Rationale:
- O usuário comum lê melhor por blocos curtos do que por um grande parágrafo institucional.
- A estrutura ajuda a equilibrar acolhimento, transparência e ação.

Alternatives considered:
- Exibir uma única descrição longa: rejeitado porque aumenta abandono e reduz escaneabilidade.
- Mostrar apenas exemplos de perguntas, sem contexto: rejeitado porque não resolve dúvidas sobre fonte, escopo e recorte temporal.

### 3. Separar “dados de transparência” de “informações úteis da cidade”

O conteúdo “o que você pode consultar” deve distinguir dois grupos:
- dados de transparência estruturados, como salários, contratos, licitações, despesas, diárias, passagens, receitas, patrimônio, frota, quadro de pessoal e eleitos
- informações institucionais e de serviço, como telefones úteis, horários de ônibus, estrutura organizacional, papel da Câmara e perguntas frequentes

Rationale:
- Essa separação traduz a fronteira atual entre base SQL e acervo curado sem expor termos técnicos como SQL ou RAG.
- Ela ajuda o cidadão a entender que o sistema responde tanto perguntas sobre números quanto perguntas de orientação pública.

Alternatives considered:
- Listar tudo em uma sequência única de itens: rejeitado porque mistura assuntos muito diferentes e reduz clareza.
- Explicar explicitamente a arquitetura SQL vs RAG na homepage: rejeitado porque isso é correto tecnicamente, mas inadequado para o público geral.

### 4. Centralizar textos públicos e faixas fixas em configuração simples

Os textos da homepage, incluindo resumo, listas, exemplos, placeholder e a faixa `2025 a maio de 2026`, devem ficar concentrados em constantes locais ou helpers de apresentação, em vez de espalhados por vários trechos de renderização.

Rationale:
- Facilita revisão editorial e futuras atualizações de conteúdo.
- Reduz o risco de inconsistência entre placeholder, exemplos e blocos informativos.

Alternatives considered:
- Escrever as strings diretamente em cada componente Streamlit: rejeitado porque dificulta manutenção.
- Calcular a faixa temporal diretamente do banco nesta etapa: rejeitado porque aumentaria o escopo e ainda dependeria do estado local da importação.

### 5. Usar exemplos acionáveis e linguagem de pergunta real

As perguntas de exemplo devem refletir formulações naturais de cidadãos, como salário de agentes públicos, gastos em contratos, receita, frota, diárias, passagens e contatos úteis. Quando clicadas, elas devem iniciar a consulta imediatamente ou preencher o fluxo do chat com o texto completo da pergunta.

Rationale:
- O exemplo vira tutorial sem exigir leitura adicional.
- Exemplos reais ajudam a calibrar expectativas melhor do que descrições abstratas.

Alternatives considered:
- Manter apenas um placeholder como orientação: rejeitado porque é pouco visível e desaparece ao digitar.
- Usar perguntas muito técnicas ou jurídicas: rejeitado porque contraria o público e o tom definidos no prompt do agente.

## Risks / Trade-offs

- [Risk] A homepage pode prometer mais cobertura do que a base local realmente tem em um dado ambiente. -> Mitigation: informar a faixa geral `2025 a maio de 2026` com ressalva curta de que a disponibilidade varia por tema e pelos arquivos já carregados.
- [Risk] Texto demais pode empurrar o campo de pergunta para baixo e atrasar a ação principal. -> Mitigation: usar blocos curtos, listas enxutas e mostrar o conteúdo completo apenas no estado inicial sem histórico.
- [Risk] A lista de exemplos pode ficar desatualizada em relação ao escopo do agente. -> Mitigation: alinhar as sugestões ao prompt ativo e revisar os exemplos sempre que novos domínios públicos forem adicionados.
- [Risk] A distinção entre transparência e informação institucional pode ficar sutil demais. -> Mitigation: nomear os grupos com linguagem simples e usar exemplos concretos em cada grupo.

## Migration Plan

1. Atualizar a homepage Streamlit para renderizar um estado inicial orientado ao cidadão quando a conversa estiver vazia.
2. Reativar ou substituir a seção de perguntas de exemplo com textos revisados em português do Brasil.
3. Atualizar o placeholder do campo de entrada para linguagem mais acolhedora e mais alinhada ao escopo real.
4. Adicionar blocos de conteúdo para dados disponíveis, origem dos dados, faixa temporal e limites da base.
5. Validar manualmente a legibilidade em desktop e mobile e revisar se o conteúdo continua coerente com o prompt e a superfície pública do agente.

Rollback strategy:
- Reverter a homepage ao cabeçalho mínimo e ao chat simples atual, removendo apenas os blocos de orientação e restaurando o placeholder anterior.

## Open Questions

- As perguntas de exemplo devem enviar a consulta diretamente ou apenas preencher o campo para a pessoa revisar antes de enviar?
- A faixa temporal `2025 a maio de 2026` ficará fixa em código nesta fase ou deve virar conteúdo editorial fácil de alterar por configuração?
- Vale incluir, já nesta primeira mudança, um aviso visual quando a base local estiver vazia ou incompleta, além da mensagem de erro já existente durante a consulta?
