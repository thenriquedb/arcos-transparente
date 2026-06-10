"""Registro central de tools com escopo, tags e metadata de roteamento."""

import importlib
import inspect
import pkgutil
import functools
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass

from agents.chatbot.observability import (
    build_error_payload,
    build_event_payload,
    get_current_observability_provider,
    summarize_result,
)
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


@dataclass(frozen=True, slots=True)
class ToolRoutingMetadata:
    """Metadados resumidos usados pelo seletor hibrido de tools."""

    summary: str
    examples: tuple[str, ...]
    hints: tuple[str, ...]
    exclusions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PublicToolCatalogEntry:
    """Entrada serializavel do catalogo publico usado no pre-selection."""

    name: str
    tool: object
    description: str
    tags: tuple[str, ...]
    routing: ToolRoutingMetadata


def routing_metadata(
    *,
    examples: Sequence[str],
    hints: Sequence[str],
    exclusions: Sequence[str] = (),
) -> dict[str, tuple[str, ...]]:
    """Atalho declarativo para metadados de roteamento em tools publicas."""

    return {
        "examples": tuple(examples),
        "hints": tuple(hints),
        "exclusions": tuple(exclusions),
    }


def register(
    func: Callable | None = None,
    *,
    name: str | None = None,
    scope: str = INTERNAL_SCOPE,
    tags: list[str] | tuple[str, ...] | None = None,
    routing: dict[str, Sequence[str]] | ToolRoutingMetadata | None = None,
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
        inner._tool_routing = _normalize_routing_metadata(
            inner,
            scope=scope,
            routing=routing,
        )
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
    tool_scope = getattr(func, "_tool_scope", INTERNAL_SCOPE)
    langchain_callable = (
        _wrap_public_tool_with_observability(func)
        if tool_scope == PUBLIC_SCOPE
        else func
    )
    langchain_tool = build_tool(tool_name)(langchain_callable)
    tags = list(getattr(func, "_tags", []))
    if tags:
        langchain_tool.tags = tags
    routing = getattr(func, "_tool_routing", None)
    if routing is not None:
        metadata = dict(getattr(langchain_tool, "metadata", {}) or {})
        metadata["routing"] = asdict(routing)
        langchain_tool.metadata = metadata

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


def get_public_tools_by_name(tool_names: Sequence[str]) -> list[object]:
    """Retorna tools publicas preservando a ordem pedida pelo seletor."""

    tools_by_name = {_tool_name(tool_obj): tool_obj for tool_obj in get_public_tools()}
    return [
        tools_by_name[tool_name]
        for tool_name in tool_names
        if tool_name in tools_by_name
    ]


def get_public_tool_catalog(
    *,
    tags: list[str] | tuple[str, ...] | None = None,
) -> list[PublicToolCatalogEntry]:
    """Retorna catalogo publico enriquecido com metadados de roteamento."""

    catalog: list[PublicToolCatalogEntry] = []
    for tool_obj in get_public_tools(tags=tags):
        metadata = dict(getattr(tool_obj, "metadata", {}) or {})
        routing_payload = metadata.get("routing")
        if not isinstance(routing_payload, dict):
            continue
        routing = ToolRoutingMetadata(
            summary=str(routing_payload.get("summary", "")).strip(),
            examples=tuple(routing_payload.get("examples", ())),
            hints=tuple(routing_payload.get("hints", ())),
            exclusions=tuple(routing_payload.get("exclusions", ())),
        )
        catalog.append(
            PublicToolCatalogEntry(
                name=_tool_name(tool_obj),
                tool=tool_obj,
                description=str(getattr(tool_obj, "description", "") or ""),
                tags=tuple(getattr(tool_obj, "tags", ()) or ()),
                routing=routing,
            )
        )
    return catalog


def get_tools_by_tag(tag: str, *, scope: str | None = None) -> list[object]:
    """Retorna tools filtradas por tag — útil para agentes especializados."""
    return [
        tool_obj for tool_obj in get_tools(scope=scope) if tag in (tool_obj.tags or [])
    ]


def _extract_doc_summary(func: Callable) -> str:
    doc = inspect.getdoc(func) or ""
    for line in doc.splitlines():
        summary = line.strip()
        if summary:
            return summary
    return getattr(func, "_tool_name", func.__name__)


def _normalize_routing_metadata(
    func: Callable,
    *,
    scope: str,
    routing: dict[str, Sequence[str]] | ToolRoutingMetadata | None,
) -> ToolRoutingMetadata | None:
    if routing is None:
        if scope == PUBLIC_SCOPE:
            raise ValueError(
                f"Public tool '{getattr(func, '_tool_name', func.__name__)}' "
                "must declare routing metadata."
            )
        return None

    if isinstance(routing, ToolRoutingMetadata):
        return routing

    examples = tuple(str(example).strip() for example in routing.get("examples", ()))
    hints = tuple(str(hint).strip() for hint in routing.get("hints", ()))
    exclusions = tuple(
        str(exclusion).strip() for exclusion in routing.get("exclusions", ())
    )
    if scope == PUBLIC_SCOPE and (not examples or not hints):
        raise ValueError(
            f"Public tool '{getattr(func, '_tool_name', func.__name__)}' "
            "must declare non-empty routing examples and hints."
        )
    return ToolRoutingMetadata(
        summary=_extract_doc_summary(func),
        examples=examples,
        hints=hints,
        exclusions=exclusions,
    )


def _wrap_public_tool_with_observability(func: Callable) -> Callable:
    signature = inspect.signature(func)
    tool_name = getattr(func, "_tool_name", func.__name__)

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        provider = get_current_observability_provider()
        bound_arguments = _bind_tool_arguments(signature, *args, **kwargs)
        with provider.span(
            "chatbot.tool",
            run_type="tool",
            inputs=build_event_payload(
                {
                    "tool_name": tool_name,
                    "tool_arguments": bound_arguments,
                }
            ),
            metadata=build_event_payload({"tool_name": tool_name}),
            tags=("chatbot", "tool", tool_name),
        ) as span:
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                span.set_metadata(
                    build_error_payload(
                        exc,
                        extra={"tool_name": tool_name, "status": "error"},
                    )
                )
                raise

            span.set_outputs(
                build_event_payload(
                    {
                        "tool_name": tool_name,
                        "status": "completed",
                        "output_summary": summarize_result(result),
                    }
                )
            )
            return result

    wrapped.__signature__ = signature
    return wrapped


def _bind_tool_arguments(
    signature: inspect.Signature,
    *args,
    **kwargs,
) -> dict[str, object]:
    try:
        return dict(signature.bind_partial(*args, **kwargs).arguments)
    except TypeError:
        return {
            "args": list(args),
            "kwargs": dict(kwargs),
        }


def _tool_name(tool_obj: object) -> str:
    return str(getattr(tool_obj, "name", getattr(tool_obj, "__name__", "")))
