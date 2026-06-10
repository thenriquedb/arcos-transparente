from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field

import pytest

import agents.chatbot.hybrid_selection as hybrid_selection
from agents.chatbot.agent import (
    criar_provider_observabilidade,
    obter_configuracao_observabilidade,
)
from agents.chatbot.core import ChatResponse, ChatbotApplication
from agents.chatbot.hybrid_selection import HybridToolSelector
from agents.chatbot.observability import NoOpObservabilityProvider


@dataclass
class RecordedSpan:
    name: str
    run_type: str
    inputs: dict[str, object]
    metadata: dict[str, object]
    tags: tuple[str, ...]
    outputs: dict[str, object] = field(default_factory=dict)
    error_type: str | None = None
    error_message: str | None = None


@dataclass
class RecordedEvent:
    name: str
    run_type: str
    inputs: dict[str, object]
    outputs: dict[str, object]
    metadata: dict[str, object]
    tags: tuple[str, ...]


class _RecordingSpanHandle:
    def __init__(self, span: RecordedSpan) -> None:
        self._span = span

    def set_outputs(self, outputs: Mapping[str, object] | None = None) -> None:
        if outputs:
            self._span.outputs.update(outputs)

    def set_metadata(self, metadata: Mapping[str, object] | None = None) -> None:
        if metadata:
            self._span.metadata.update(metadata)

    def record_error(self, error: BaseException) -> None:
        self._span.error_type = error.__class__.__name__
        self._span.error_message = str(error)


class RecordingObservabilityProvider:
    name = "recording"

    def __init__(self) -> None:
        self.completed_spans: list[RecordedSpan] = []
        self.emitted_events: list[RecordedEvent] = []

    @contextmanager
    def span(
        self,
        name: str,
        *,
        run_type: str = "chain",
        inputs: Mapping[str, object] | None = None,
        metadata: Mapping[str, object] | None = None,
        tags: Sequence[str] | None = None,
    ) -> Iterator[_RecordingSpanHandle]:
        span = RecordedSpan(
            name=name,
            run_type=run_type,
            inputs=dict(inputs or {}),
            metadata=dict(metadata or {}),
            tags=tuple(tags or ()),
        )
        handle = _RecordingSpanHandle(span)
        try:
            yield handle
        except Exception as exc:
            handle.record_error(exc)
            raise
        finally:
            self.completed_spans.append(span)

    def emit_event(
        self,
        name: str,
        *,
        run_type: str = "chain",
        inputs: Mapping[str, object] | None = None,
        outputs: Mapping[str, object] | None = None,
        metadata: Mapping[str, object] | None = None,
        tags: Sequence[str] | None = None,
    ) -> None:
        self.emitted_events.append(
            RecordedEvent(
                name=name,
                run_type=run_type,
                inputs=dict(inputs or {}),
                outputs=dict(outputs or {}),
                metadata=dict(metadata or {}),
                tags=tuple(tags or ()),
            )
        )


class StaticSelectionBackend:
    def answer_with_selection(
        self,
        question: str,
        *,
        session_id: str,
        selection=None,
    ) -> ChatResponse:
        _ = session_id
        tool_names = list(selection.candidate_tool_names) if selection else []
        return ChatResponse(
            content=f"resposta para: {question}",
            metadata={"selected_tool_names": tool_names},
        )


class ExplodingBackend:
    def answer_with_selection(
        self,
        question: str,
        *,
        session_id: str,
        selection=None,
    ) -> ChatResponse:
        _ = (question, session_id, selection)
        raise RuntimeError("backend explodiu")


def test_obter_configuracao_observabilidade_retorna_noop_quando_desabilitada(
    monkeypatch,
) -> None:
    monkeypatch.delenv("OBSERVABILITY_ENABLED", raising=False)
    monkeypatch.delenv("OBSERVABILITY_PROVIDER", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.delenv("LANGSMITH_ENDPOINT", raising=False)

    config = obter_configuracao_observabilidade()
    provider = criar_provider_observabilidade()

    assert config.enabled is False
    assert config.provider == "noop"
    assert isinstance(provider, NoOpObservabilityProvider)


def test_criar_provider_observabilidade_constroi_langsmith(monkeypatch) -> None:
    import langsmith.client as langsmith_client

    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(langsmith_client, "Client", FakeClient)
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("OBSERVABILITY_PROVIDER", "langsmith")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-key")
    monkeypatch.setenv("LANGSMITH_PROJECT", "arcos-tests")
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "https://smith.example.com")

    provider = criar_provider_observabilidade()

    assert provider.name == "langsmith"
    assert captured == {
        "api_key": "ls-key",
        "api_url": "https://smith.example.com",
    }


def test_observabilidade_langsmith_rejeita_api_key_ausente(monkeypatch) -> None:
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("OBSERVABILITY_PROVIDER", "langsmith")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setenv("LANGSMITH_PROJECT", "arcos-tests")

    with pytest.raises(
        ValueError,
        match=("LANGSMITH_API_KEY deve ser informado quando OBSERVABILITY_PROVIDER=langsmith\\."),
    ):
        criar_provider_observabilidade()


def test_observabilidade_rejeita_provider_nao_suportado(monkeypatch) -> None:
    monkeypatch.setenv("OBSERVABILITY_ENABLED", "true")
    monkeypatch.setenv("OBSERVABILITY_PROVIDER", "langfuse")

    with pytest.raises(
        ValueError,
        match=(
            "Provider de observabilidade nao suportado: langfuse\\. "
            "Providers suportados nesta fase: noop, langsmith\\."
        ),
    ):
        criar_provider_observabilidade()


def test_chatbot_emit_eventos_para_consulta_bloqueada() -> None:
    provider = RecordingObservabilityProvider()
    app = ChatbotApplication(
        backend=StaticSelectionBackend(),
        observability_provider=provider,
    )

    response = app.ask("Como implementar uma lista encadeada em Python?")

    assert response.guardrail_triggered is True
    policy_event = next(event for event in provider.emitted_events if event.name == "chatbot.policy")
    request_span = next(span for span in provider.completed_spans if span.name == "chatbot.request")

    assert policy_event.outputs["policy_action"] == "block"
    assert request_span.outputs["status"] == "blocked"
    assert request_span.outputs["guardrail_triggered"] is True


def test_chatbot_emit_eventos_para_consulta_permitida_com_selecao(
    monkeypatch,
) -> None:
    provider = RecordingObservabilityProvider()
    monkeypatch.setattr(
        hybrid_selection,
        "_select_with_heuristics",
        lambda *_args, **_kwargs: None,
    )
    selector = HybridToolSelector(
        runner=lambda *_args: {
            "action": "allow",
            "candidate_tool_names": ["consultar_contratos"],
            "confidence": "high",
            "reason_code": "unit_test",
        },
        observability_provider=provider,
    )
    app = ChatbotApplication(
        backend=StaticSelectionBackend(),
        selector=selector,
        observability_provider=provider,
    )

    response = app.ask("mostre contratos em 2025")

    assert "resposta para" in response.content
    selection_event = next(event for event in provider.emitted_events if event.name == "chatbot.selection")
    request_span = next(span for span in provider.completed_spans if span.name == "chatbot.request")

    assert selection_event.outputs["selection_action"] == "allow"
    assert selection_event.outputs["selected_tool_names"] == ["consultar_contratos"]
    assert request_span.outputs["status"] == "completed"
    assert request_span.outputs["selected_tool_names"] == ["consultar_contratos"]


def test_chatbot_registra_falha_surfaced_no_request_span(monkeypatch) -> None:
    provider = RecordingObservabilityProvider()
    monkeypatch.setattr(
        hybrid_selection,
        "_select_with_heuristics",
        lambda *_args, **_kwargs: None,
    )
    selector = HybridToolSelector(
        runner=lambda *_args: {
            "action": "allow",
            "candidate_tool_names": ["consultar_contratos"],
            "confidence": "high",
            "reason_code": "unit_test",
        },
        observability_provider=provider,
    )
    app = ChatbotApplication(
        backend=ExplodingBackend(),
        selector=selector,
        observability_provider=provider,
    )

    with pytest.raises(RuntimeError, match="backend explodiu"):
        app.ask("mostre contratos em 2025")

    request_span = next(span for span in provider.completed_spans if span.name == "chatbot.request")

    assert request_span.error_type == "RuntimeError"
    assert request_span.metadata["status"] == "error"
    assert request_span.metadata["error_type"] == "RuntimeError"
