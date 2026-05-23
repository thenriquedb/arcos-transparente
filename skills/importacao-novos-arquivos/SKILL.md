---
name: importacao-novos-arquivos
description: Use quando for adicionar um novo tipo de arquivo XML, adaptar uma fonte existente ou expandir a ingestao do Arcos Transparente com parser, schema Pydantic, migration, registro no pipeline, testes e tools opcionais.
---

# Importacao de Novos Arquivos

Use esta skill ao criar ou alterar fluxos de importacao do projeto.

Leia `references/projeto.md` antes de editar arquivos.

## Fluxo padrao

1. Entenda a fonte:
   - confirme se o XML entra em um tipo existente ou se precisa de um novo tipo no pipeline
   - identifique campos obrigatorios, relacionamento entre registros e formato de datas e valores
2. Modele a ingestao:
   - crie ou ajuste o parser em `ingestion/parsers/xml/`
   - crie schema Pydantic em `ingestion/schemas/` quando houver normalizacao, defaults ou validacao relevante
   - reuse helpers de `shared/utils/validation.py` antes de criar novas funcoes
3. Modele persistencia:
   - crie ou ajuste modelo SQLAlchemy
   - crie migration Alembic para tabelas, colunas, indices e constraints
   - registre parser e modelo em `ingestion/pipeline.py`
   - se o dominio exigir carga especial, siga o padrao de ramo dedicado do pipeline em vez do fluxo generico
4. Valide o contrato:
   - parser deve devolver tipos Python prontos para persistencia
   - valores monetarios devem sair como `Decimal`
   - datas devem sair como `date`
   - campos textuais devem ser saneados com `strip` e vazio para `None`
5. Feche com testes e smoke:
   - schema unitario
   - parser com fixture realista
   - testes de pipeline/loader quando houver logica nao trivial
   - smoke import com `cli.py importar`

## Regras que ja viraram padrao no projeto

- Use Pydantic v2 como camada de validacao entre parser e persistencia.
- Quando fizer sentido, descarte filhos invalidos sem derrubar o registro pai.
- Mantenha nomes tecnicos no banco e no ORM quando isso preservar a semantica correta.
- Em tools publicas, prefira linguagem simples:
  - `mes_de_referencia` em vez de `competencia`
  - `setor` em vez de `lotacao`
  - `ganhos`, `adicionais` e `valor_recebido` em vez de termos internos da folha
- Para novas tools SQL:
  - crie schemas Pydantic em `agents/tools/sql_tools/*_schemas.py`
  - use resposta estruturada com `query`, `total`, `resultados`, `mensagem` e `sugestao`
  - exponha contratos em linguagem leiga, mesmo quando a query interna use nomes tecnicos

## Quando expandir alem da ingestao

Se o novo arquivo tambem precisar ser consultado pelo agente:

- crie tool SQL dedicada
- mantenha o contrato publico consistente com os nomes simples ja adotados
- cubra a tool com testes especificos

## Entrega esperada

Ao concluir a implementacao:

- explique a semantica escolhida
- liste os comandos de validacao executados
- registre qualquer suposicao de modelagem
- aponte se houve smoke import real ou apenas testes locais
