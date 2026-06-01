import importlib
import pkgutil
from collections.abc import Callable

from langchain.tools import tool as build_tool

TOOLS_PACKAGES = (
    "agents.tools.sql_tools",
    "agents.tools.rag_tools",
)
PUBLIC_SCOPE = "public"
INTERNAL_SCOPE = "internal"

_REGISTRY: list[Callable] = []
_TOOL_CACHE: dict[Callable, object] = {}
_DISCOVERED = False


def register(
    func: Callable | None = None,
    *,
    name: str | None = None,
    scope: str = INTERNAL_SCOPE,
    tags: list[str] | tuple[str, ...] | None = None,
):
    """Registra funções Python e converte para tool do LangChain só no bootstrap."""

    def decorator(inner: Callable) -> Callable:
        inner._tool_name = name or inner.__name__
        inner._tool_scope = scope
        normalized_tags = list(tags or [])
        scope_tag = f"scope:{scope}"
        if scope_tag not in normalized_tags:
            normalized_tags.append(scope_tag)
        inner._tags = normalized_tags
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

    for package_name in TOOLS_PACKAGES:
        package = importlib.import_module(package_name)
        for module_info in pkgutil.walk_packages(
            package.__path__,
            prefix=f"{package_name}.",
        ):
            importlib.import_module(module_info.name)

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


def get_tools(
    *,
    scope: str | None = None,
    tags: list[str] | tuple[str, ...] | None = None,
) -> list[object]:
    """Retorna tools filtradas por escopo e/ou conjunto de tags."""

    filtered_tools = get_all_tools()

    if scope is not None:
        filtered_tools = [
            tool_obj
            for tool_obj in filtered_tools
            if f"scope:{scope}" in (tool_obj.tags or [])
        ]

    if tags:
        required_tags = set(tags)
        filtered_tools = [
            tool_obj
            for tool_obj in filtered_tools
            if required_tags.issubset(set(tool_obj.tags or []))
        ]

    return filtered_tools


def get_public_tools(
    *, tags: list[str] | tuple[str, ...] | None = None
) -> list[object]:
    """Retorna apenas as tools publicas."""

    return get_tools(scope=PUBLIC_SCOPE, tags=tags)


def get_tools_by_tag(tag: str, *, scope: str | None = None) -> list[object]:
    """Retorna tools filtradas por tag — útil para agentes especializados."""
    return [
        tool_obj for tool_obj in get_tools(scope=scope) if tag in (tool_obj.tags or [])
    ]
