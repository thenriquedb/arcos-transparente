## 1. Estruturar o conteúdo público da homepage

- [x] 1.1 Definir em `agents/chatbot/web.py` ou em helper próximo um conjunto centralizado de textos públicos para resumo, placeholder, exemplos de perguntas, grupos de dados disponíveis, origem dos dados, faixa temporal `2025 a maio de 2026` e aviso de limites da base.
- [x] 1.2 Revisar os textos definidos para garantir português do Brasil, linguagem cidadã e coerência com o escopo real do chatbot descrito no prompt e nas capacidades já suportadas.

## 2. Implementar o estado inicial orientado ao cidadão

- [x] 2.1 Atualizar a homepage Streamlit para renderizar um estado inicial com resumo breve, perguntas de exemplo e seções de orientação quando não houver mensagens na sessão.
- [x] 2.2 Reativar ou substituir as perguntas de exemplo para que funcionem como ações de início rápido da conversa, usando textos cotidianos e cobrindo múltiplos domínios do produto.
- [x] 2.3 Atualizar o placeholder do campo de chat e os blocos de “o que você pode consultar”, “de onde vêm os dados” e “qual período está disponível”, mantendo o chat como foco principal após a primeira interação.

## 3. Validar comportamento e qualidade da experiência

- [x] 3.1 Adicionar ou atualizar testes em `tests/agents/test_chatbot_web.py` para cobrir a renderização do estado inicial, a presença das orientações principais e o acionamento das perguntas de exemplo.
- [x] 3.2 Validar manualmente a homepage em execução local para conferir legibilidade, ordem dos blocos, clareza do texto e comportamento antes e depois da primeira pergunta.
