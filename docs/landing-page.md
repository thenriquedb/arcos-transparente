**# Arcos Transparente — Prompt para Geração da Landing Page

## Stack

- Framework: Next.js 14 com App Router
- Estilização: Tailwind CSS
- Ícones: Lucide React
- Animações: Tailwind e CSS puro
- Deploy: Vercel
- Página estática — sem banco de dados, sem autenticação

---

## Identidade Visual

- Cor primária: azul institucional (deve ser para alteraçao facil)
- Tom: institucional mas acessível — sem parecer site de startup nem portal
  governamental antiquado
- Tipografia: Inter — legível, sem serifa, neutra
- Fundo: branco com superfícies cinza muito claro para separação de seções
- NÃO usar: gradientes, animações excessivas, dark mode, imagens de stock,
  fotos genéricas de "cidadão sorrindo"

---

## Estrutura da Página

Ordem das seções — respeitar exatamente esta sequência:

1. Header fixo
2. Hero com simulação de chat (ver especificação detalhada abaixo)
3. O problema
4. Como funciona
5. O que você pode perguntar
6. Os dados disponíveis
7. Por que isso importa
8. Sobre o criador
9. CTA final
10. Footer

---

## Especificação do Hero — Simulação de Chat com Typewriter

O hero deve ter layout dividido em duas colunas no desktop:

- Coluna esquerda (40%): headline, subtítulo e botões de CTA
- Coluna direita (60%): simulação de chat animada

No mobile, as colunas empilham — simulação de chat aparece abaixo do texto.

### Componente de simulação de chat

Renderizar um balão de interface de chat que simula uma conversa real com o
assistente. O componente deve:

**Aparência:**
- Fundo levemente acinzentado com bordas arredondadas — simular uma janela
  de chat real
- Header do chat com nome "Arcos Transparente" e indicador de status verde
  "online"
- Balões de mensagem do usuário alinhados à direita, cor primária azul,
  texto branco
- Balões de resposta do assistente alinhados à esquerda, fundo branco com
  borda sutil
- Avatar do assistente: ícone de prédio/governo pequeno à esquerda das
  respostas

**Animação — sequência obrigatória e cíclica:**

A animação deve rodar em loop infinito, passando por 3 pares de
pergunta e resposta em sequência. Entre cada ciclo, aguardar 2 segundos
antes de reiniciar.

Pares de conversa a usar:

```
Par 1:
  Usuário: "Qual o salário do prefeito de Arcos?"
  Assistente: "Segundo os dados da folha de pagamento, o prefeito
               recebeu R$ 14.283,50 líquido em março de 2025,
               incluindo subsídio e descontos."

Par 2:
  Usuário: "Qual empresa ganhou mais contratos em 2024?"
  Assistente: "Em 2024, a empresa com mais contratos firmados foi
               [Empresa X], com 12 contratos totalizando
               R$ 1.240.000,00 em valores contratados."

Par 3:
  Usuário: "Quanto foi gasto com saúde no primeiro trimestre de 2025?"
  Assistente: "No primeiro trimestre de 2025, a Secretaria de Saúde
               registrou R$ 4.182.340,00 em despesas empenhadas,
               conforme os dados de planejamento importados."
```

**Sequência de cada par:**
1. Balão do usuário aparece com fade in (200ms)
2. Aguardar 400ms
3. Indicador de digitação aparece no balão do assistente ("..." piscando)
4. Aguardar 800ms — simular o assistente "pensando"
5. Texto da resposta aparece caractere por caractere — efeito typewriter
   a 30ms por caractere
6. Aguardar 2.500ms com a resposta completa visível
7. Fade out suave de todos os balões (300ms)
8. Próximo par começa

**Comportamento:**
- A animação inicia automaticamente ao carregar a página
- Pausar animação quando o elemento não está visível (Intersection Observer)
- Respeitar `prefers-reduced-motion` — se ativo, mostrar os três pares
  estáticos sem animação, apenas o último par visível
- Não há interação do usuário com este componente — é puramente ilustrativo

**Rodapé do componente de chat:**
- Campo de input desabilitado com placeholder "Faça sua pergunta..."
- Botão "Enviar" desabilitado
- Texto abaixo: "Experimente você mesmo →" com link para __URL_CHATBOT__

---

## Copy das Seções

### Header
- Logo: "Arcos Transparente" em texto
- Links: GitHub
- Botão: "Experimente →" → __URL_CHATBOT__ (nova aba)

### Hero — coluna esquerda

**Transparência pública que qualquer pessoa consegue usar.**

Pergunte, em português, sobre as contas públicas de Arcos (MG) — contratos,
salários, licitações, despesas e mais. Sem planilhas, sem juridiquês.

[ Experimente o chatbot → ](__URL_CHATBOT__)  ·  [ Ver no GitHub ](__LINK_GITHUB__)

### O problema

**Os dados são públicos. Mas estão longe de você.**

As contas da prefeitura ficam espalhadas em portais, planilhas que
pouca gente sabe abrir. Saber quanto foi gasto numa obra, quem ganhou uma
licitação ou qual o salário de um cargo vira um trabalho de investigador.

O Arcos Transparente tira esse trabalho do seu caminho.

### Como funciona

**Funciona como uma conversa.**

1. Você pergunta em português, do seu jeito — "quanto a saúde gastou em 2025?".
2. Ele busca nos dados oficiais do município e cruza várias fontes quando preciso.
3. Você recebe a resposta com os números e a fonte — período e origem citados.

Usar o stepper visual 1 → 2 → 3 com ícone para cada etapa.

> Toda resposta indica de onde veio o dado.

### O que você pode perguntar

**Não sabe por onde começar? Pergunte algo assim:**

Cards clicáveis — ao clicar, copiar o texto para o clipboard com feedback
visual "Copiado!" por 1.5 segundos.

Dinheiro e contratos:
- "Quais os 10 maiores contratos de 2025?"
- "Quanto a Secretaria de Saúde contratou no ano?"
- "Quais fornecedores têm mais contratos?"

Salários e pessoal:
- "Quais os 10 maiores salários do município?"
- "Qual o salário do prefeito?"
- "Quantas pessoas trabalham na saúde?"

Licitações e eventos:
- "Quanto custou a Fest de Natal somando contratos e despesas?"
- "Quem venceu a licitação 147/2025?"

Frota e patrimônio:
- "Quais veículos geram mais gasto de manutenção?"

### Os dados disponíveis

**Tudo num só lugar.**

Grid de chips/tags com os domínios disponíveis:

Contratos · Licitações · Despesas · Receitas · Salários e folha de pagamento ·
Servidores · Servidores e cargos da Câmara · Diárias e passagens · Frota e
manutenção de veículos · Patrimônio · Estoque e almoxarifado · Quadro de pessoal ·
Planejamento orçamentário · Transferências e emendas · Vereadores e prefeitos
eleitos · Telefones úteis · Horários de ônibus

Deve ter um texto cinza discreto sobre o range dos dados (Janeiro de 2025 - Maio de 2026)

### Por que isso importa

**Fiscalizar não devia ser privilégio de especialista.**

Quando qualquer pessoa consegue perguntar para onde vai o dinheiro público, o
controle social deixa de depender de quem entende de planilha.

Para jornalistas, é um atalho para a próxima reportagem. Para o cidadão, é o
direito de saber.

### Sobre o criador

Layout duas colunas — foto/avatar à esquerda, texto à direita.

Sou **__NOME__**, **__CARGO__**. Construí o Arcos Transparente para provar,
na prática, que dados públicos podem ser fáceis de consultar — e para colocar
isso nas mãos de quem mora aqui.

[ GitHub ](__LINK_GITHUB__) · [ LinkedIn ](#) · [ E-mail ](mailto:__EMAIL__)

### CTA final

**Pronto para experimentar?**

[ Experimente o chatbot → ](__URL_CHATBOT__)

É jornalista e quer conversar sobre o projeto? Fale comigo: __EMAIL__

### Footer

Dados do portal de transparência de Arcos (MG). Projeto independente, sem
vínculo oficial com a prefeitura. Código aberto sob licença AGPL-3.0 ·
[ Repositório ](__LINK_GITHUB__)

---

## CTAs e Links

- Todo link externo abre em nova aba (`target="_blank" rel="noopener"`)
- Botão primário: fundo azul, texto branco, hover escurece 10%
- Botão secundário: borda azul, fundo transparente
- Botão flutuante fixo no mobile: "Experimente →" aparece após rolar além
  do hero, some ao chegar no CTA final

---

## Responsividade

- Mobile first
- Breakpoints: mobile < 768px, tablet 768–1024px, desktop > 1024px
- Hero: duas colunas no desktop, empilhado no mobile (texto → chat)
- Simulação de chat no mobile: altura máxima de 320px com scroll interno
  se necessário
- Fonte mínima: 16px

---

## SEO e Metadados

- Title: "Arcos Transparente — Consulte os dados públicos de Arcos (MG)"
- Description: "Ferramenta gratuita para consultar contratos, salários e
  licitações da prefeitura de Arcos em linguagem natural."
- OG Image: gerar preview para compartilhamento social com nome e tagline
- Canonical URL: domínio de produção

---

## Interações

- Cards de exemplo (seção 4): clique copia texto para clipboard com
  feedback "Copiado!" por 1.5s
- Header: transparente no topo, fundo branco com sombra sutil ao rolar
- Seções: fade in suave ao entrar no viewport (Framer Motion)
  — apenas nas seções, não em cada elemento individual

---

## Acessibilidade

- Alt text em todas as imagens
- Contraste mínimo WCAG AA
- Foco visível em todos os elementos interativos
- Simulação de chat: `aria-label="Demonstração do assistente"` e
  `aria-live="polite"` na área de resposta
- Respeitar `prefers-reduced-motion` em todas as animações

---

## Restrições

- NÃO criar formulário de cadastro — não há backend
- NÃO prometer dados em tempo real — usar "dados atualizados periodicamente"
- NÃO usar imagens de stock
- Manter placeholders `__URL_CHATBOT__` e `__LINK_GITHUB__` como constantes
  no topo do arquivo para fácil substituição
- NÃO adicionar seções além das listadas na estrutura
- NÃO usar bibliotecas além das especificadas na stack**