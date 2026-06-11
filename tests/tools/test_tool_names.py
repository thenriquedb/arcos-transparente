from __future__ import annotations

from agents.tools.names import ToolName
from agents.tools.registry import get_public_tools, get_public_tools_by_name


def _registered_public_tool_names() -> set[str]:
    return {str(getattr(tool_obj, "name", "")) for tool_obj in get_public_tools()}


def test_tool_name_enum_matches_registry_exactly() -> None:
    # Fonte única da verdade: o enum e o registry de tools públicas não podem divergir.
    # Se uma tool for adicionada, renomeada ou removida sem atualizar `ToolName`,
    # este teste falha — impedindo que a seleção aponte para um nome inexistente.
    enum_names = {member.value for member in ToolName}
    registered = _registered_public_tool_names()

    assert enum_names == registered, {
        "faltando_no_enum": registered - enum_names,
        "faltando_no_registry": enum_names - registered,
    }


def test_every_tool_name_resolves_para_uma_tool_publica() -> None:
    for member in ToolName:
        resolved = get_public_tools_by_name([member])
        assert len(resolved) == 1, f"{member!r} não resolveu para exatamente uma tool"
        assert str(getattr(resolved[0], "name", "")) == member.value


def test_tool_name_membro_e_uma_string_real() -> None:
    # StrEnum: o membro deve se comportar como a string pura em comparações e str().
    assert ToolName.CONSULTAR_CONTRATOS == "consultar_contratos"
    assert str(ToolName.CONSULTAR_CONTRATOS) == "consultar_contratos"
