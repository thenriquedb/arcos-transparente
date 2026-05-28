from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

from agents.chatbot.core import ChatResponse
import agents.chatbot.web as chatbot_web


class FakeSessionState(dict):
    def __getattr__(self, name: str):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value) -> None:
        self[name] = value


class FakeStreamlit:
    def __init__(self, app) -> None:
        self.session_state = FakeSessionState(
            app=app,
            messages=[],
            is_loading=False,
        )
        self.markdown_calls: list[str] = []

    def chat_message(self, _role: str):
        return nullcontext()

    def markdown(self, content: str) -> None:
        self.markdown_calls.append(content)

    def warning(self, content: str) -> None:
        self.markdown_calls.append(content)

    def error(self, content: str) -> None:
        self.markdown_calls.append(content)

    def expander(self, _label: str):
        return nullcontext()

    def code(self, content: str) -> None:
        self.markdown_calls.append(content)


class FakeApp:
    def __init__(self) -> None:
        self.ask_calls: list[str] = []

    def ask(self, prompt: str) -> ChatResponse:
        self.ask_calls.append(prompt)
        return ChatResponse(content="Resposta final limpa.")

    def stream(self, _prompt: str):
        raise AssertionError("A interface web nao deve renderizar stream do agente.")


def test_handle_prompt_web_renderiza_apenas_resposta_final(monkeypatch) -> None:
    app = FakeApp()
    fake_st = FakeStreamlit(app)
    monkeypatch.setattr(chatbot_web, "st", fake_st)

    chatbot_web.handle_prompt("quem é o prefeito?")

    assert app.ask_calls == ["quem é o prefeito?"]
    assert fake_st.markdown_calls == [
        "quem é o prefeito?",
        "Resposta final limpa.",
    ]
    assert fake_st.session_state.messages == [
        {"role": "user", "content": "quem é o prefeito?"},
        {"role": "assistant", "content": "Resposta final limpa."},
    ]
    assert fake_st.session_state.is_loading is False


def test_ensure_session_state_recria_app_quando_prompt_ou_tools_mudam(
    monkeypatch,
) -> None:
    calls: list[tuple[str, str]] = []

    fake_st = SimpleNamespace(
        session_state=FakeSessionState(
            chat_session_id="sessao-web",
            backend_cache_token="token-antigo",
            app="app-antigo",
            messages=[],
            is_loading=False,
        )
    )

    def fake_build_application(session_id: str, cache_token: str):
        calls.append((session_id, cache_token))
        return "app-novo"

    monkeypatch.setattr(chatbot_web, "st", fake_st)
    monkeypatch.setattr(
        chatbot_web,
        "build_backend_cache_token",
        lambda: "token-novo",
    )
    monkeypatch.setattr(chatbot_web, "build_application", fake_build_application)

    chatbot_web.ensure_session_state()

    assert calls == [("sessao-web", "token-novo")]
    assert fake_st.session_state.backend_cache_token == "token-novo"
    assert fake_st.session_state.app == "app-novo"
