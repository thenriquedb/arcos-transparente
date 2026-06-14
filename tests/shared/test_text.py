from __future__ import annotations

from shared.utils.text import matches_text_query, normalize_search_text


def test_normalize_search_text_remove_acentos_e_caixa() -> None:
    assert normalize_search_text("  Vigilância Sanitária  ") == "  vigilancia sanitaria  "


def test_matches_text_query_tolera_plural_irregular_em_frase() -> None:
    texto = "Valor que se empenha referente aluguel de imóvel destinado a Vigilância Sanitária."

    assert matches_text_query(texto, "aluguel de imóveis")
    assert matches_text_query(texto, "imóveis")


def test_matches_text_query_tolera_plural_irregular_em_termo_unico() -> None:
    assert matches_text_query("Pagamento de aluguel de imóvel funcional.", "aluguéis")


def test_matches_text_query_nao_faz_fuzzy_em_nome_proprio() -> None:
    assert not matches_text_query("Marco Vinicius", "Marcos Vinicius")
