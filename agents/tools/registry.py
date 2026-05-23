import importlib
import pkgutil
from collections.abc import Callable

from langchain.tools import tool as build_tool

TOOLS_PACKAGE = "agents.tools.sql_tools"

_REGISTRY: list[Callable] = []
_TOOL_CACHE: dict[Callable, object] = {}
_DISCOVERED = False


def register(
    func: Callable | None = None,
    *,
    name: str | None = None,
    tags: list[str] | tuple[str, ...] | None = None,
):
    """Registra funções Python e converte para tool do LangChain só no bootstrap."""

    def decorator(inner: Callable) -> Callable:
        inner._tool_name = name or inner.__name__
        inner._tags = list(tags or [])
        if inner not in _REGISTRY:
            _REGISTRY.append(inner)
        return inner

    if func is None:
        return decorator
    return decorator(func)


def _discover_tool_modules() -> None:
    """Importa módulos de tools para disparar os decorators de registro."""
    global _DISCOVERED

    if _DISCOVERED:
        return

    package = importlib.import_module(TOOLS_PACKAGE)
    for module_info in pkgutil.iter_modules(package.__path__):
        importlib.import_module(f"{TOOLS_PACKAGE}.{module_info.name}")

    _DISCOVERED = True


def _to_langchain_tool(func: Callable):
    cached_tool = _TOOL_CACHE.get(func)
    if cached_tool is not None:
        return cached_tool

    tool_name = getattr(func, "_tool_name", func.__name__)
    langchain_tool = build_tool(tool_name)(func)
    tags = list(getattr(func, "_tags", []))
    if tags:
        langchain_tool.tags = tags

    _TOOL_CACHE[func] = langchain_tool
    return langchain_tool


def get_all_tools() -> list[object]:
    """Retorna todas as tools registradas como tools do LangChain."""
    _discover_tool_modules()
    return [_to_langchain_tool(func) for func in _REGISTRY]


def get_tools_by_tag(tag: str) -> list[object]:
    """Retorna tools filtradas por tag — útil para agentes especializados."""
    return [tool_obj for tool_obj in get_all_tools() if tag in (tool_obj.tags or [])]
