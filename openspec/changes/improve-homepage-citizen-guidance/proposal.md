## Why

A homepage atual do Arcos Transparente abre praticamente direto no chat e oferece pouca orientação para quem chega sem conhecer o projeto, os dados disponíveis ou o tipo de pergunta que pode fazer. Isso cria insegurança logo no primeiro contato e reduz a chance de uso por pessoas comuns, especialmente quando o objetivo é consultar gastos, servidores, receitas ou informações institucionais sem linguagem técnica.

## What Changes

- Reestruturar a homepage do chat para funcionar como uma porta de entrada mais acolhedora, com resumo breve do serviço em linguagem simples e foco em utilidade pública.
- Exibir perguntas de exemplo mais próximas do vocabulário cotidiano da população, cobrindo consultas sobre salários, contratos, receitas, diárias, passagens, patrimônio, frota e informações institucionais.
- Atualizar o placeholder do campo de pergunta para orientar melhor o tipo de assunto aceito pelo sistema.
- Explicar, de forma visível, quais conjuntos de dados podem ser consultados, separando dados estruturados de transparência e informações institucionais do acervo curado.
- Informar a origem dos dados em termos acessíveis, deixando claro que a base reúne dados públicos importados de arquivos locais derivados dos portais e fontes públicas do município.
- Exibir a faixa temporal disponível na homepage, com texto inicial informando cobertura de 2025 até maio de 2026.
- Incluir avisos úteis para o cidadão, como limites da base, possibilidade de ausência de registros e incentivo para formular perguntas curtas e objetivas.

## Capabilities

### New Capabilities
- `homepage-citizen-guidance`: Define a homepage inicial em português do Brasil, com apresentação cidadã, exemplos de perguntas, orientação de uso, transparência sobre cobertura dos dados e contexto suficiente para que a pessoa saiba o que pode consultar antes de começar a conversa.

### Modified Capabilities
- None.

## Impact

- Affected code: `agents/chatbot/web.py` e eventuais helpers de apresentação usados pela interface Streamlit.
- Affected behavior: a primeira experiência da pessoa usuária antes do envio da primeira pergunta, incluindo textos de boas-vindas, sugestões, placeholder e explicação da cobertura da base.
- Affected content: mensagens públicas em português do Brasil, lista de exemplos, descrição dos dados disponíveis, origem dos dados e faixa temporal visível na homepage.
- Risk areas: excesso de informação acima da dobra, divergência entre a homepage e a superfície real de consultas do agente, e desatualização manual da faixa temporal ou da lista de dados disponíveis.
