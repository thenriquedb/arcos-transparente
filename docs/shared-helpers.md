# Shared Helpers

Este projeto usa uma regra simples para extrair helpers reutilizaveis:

- Use `shared/` apenas para helpers realmente transversais entre subsistemas.
- Use um `shared/` local dentro do subsistema quando a reutilizacao estiver restrita a uma area, como `agents/tools/sql_tools/shared/` ou `ingestion/schemas/shared/`.
- Mantenha logica de negocio especifica do dominio perto do caller e extraia apenas a parte generica de saneamento, parsing ou serializacao.

## Aplicacao Atual

- `shared/utils/validation.py`: parsing e validacao reutilizados por ingestao e tools SQL, como `parse_int` e `parse_month`.
- `agents/tools/sql_tools/shared/`: base comum e normalizadores de schemas das tools SQL.
- `ingestion/schemas/shared/`: normalizacao de listas aninhadas que descartam filhos invalidos sem rejeitar o registro pai.

## Regra Pratica

Antes de mover um helper, confirme:

1. Ele e puro ou quase puro.
2. Ele aparece em mais de um caller real.
3. O destino mais estreito ainda cobre todos os usos conhecidos.
