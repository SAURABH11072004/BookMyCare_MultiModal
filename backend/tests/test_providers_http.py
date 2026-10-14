"""Request/response handling of remote providers, with the HTTP layer stubbed
(no network, no real keys)."""
import json

import pytest

from app.ai import remote
from app.ai.base import ImageInput, LLMRequest, ProviderError
from app.core.config import get_settings


@pytest.fixture
def keys(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "gemini_api_key", "g-key")
    monkeypatch.setattr(s, "groq_api_key", "q-key")
    monkeypatch.setattr(s, "openrouter_api_key", "o-key")


def test_gemini_payload_and_parsing(monkeypatch, keys):
    seen = {}

    def fake_post(url, headers, payload):
        seen.update(url=url, headers=headers, payload=payload)
        return {"candidates": [{"content": {"parts": [{"text": '{"summary": "ok"}'}]}}]}

    monkeypatch.setattr(remote, "_post", fake_post)
    req = LLMRequest(task="t", system="sys", prompt="hi", images=[ImageInput("image/png", b"\x89PNG")])
    resp = remote.GeminiProvider().generate(req)
    assert resp.data == {"summary": "ok"} and resp.provider == "gemini"
    assert seen["headers"]["x-goog-api-key"] == "g-key"
    assert "key=" not in seen["url"]  # key is sent as a header, not in the URL
    parts = seen["payload"]["contents"][0]["parts"]
    assert parts[1]["inline_data"]["mime_type"] == "image/png"
    assert seen["payload"]["generationConfig"]["responseMimeType"] == "application/json"


def test_gemini_blocked_response(monkeypatch, keys):
    monkeypatch.setattr(remote, "_post", lambda *a: {"promptFeedback": {"blockReason": "SAFETY"}})
    with pytest.raises(ProviderError, match="SAFETY"):
        remote.GeminiProvider().generate(LLMRequest(task="t", system="s", prompt="p"))


@pytest.mark.parametrize("cls,base,key", [(remote.GroqProvider, "api.groq.com", "q-key"), (remote.OpenRouterProvider, "openrouter.ai", "o-key")])
def test_openai_compatible(monkeypatch, keys, cls, base, key):
    seen = {}

    def fake_post(url, headers, payload):
        seen.update(url=url, headers=headers, payload=payload)
        return {"choices": [{"message": {"content": json.dumps({"summary": "x"})}}]}

    monkeypatch.setattr(remote, "_post", fake_post)
    resp = cls().generate(LLMRequest(task="t", system="sys", prompt="p"))
    assert resp.data == {"summary": "x"}
    assert base in seen["url"] and seen["headers"]["Authorization"] == f"Bearer {key}"
    assert seen["payload"]["messages"][0] == {"role": "system", "content": "sys"}
    with pytest.raises(ProviderError, match="does not support image"):
        cls().generate(LLMRequest(task="t", system="s", prompt="p", images=[ImageInput("image/png", b"x")]))


def test_http_errors_become_provider_errors(monkeypatch, keys):
    import httpx

    class R:
        status_code = 429
        text = "rate limited"

    monkeypatch.setattr(httpx, "post", lambda *a, **k: R())
    with pytest.raises(ProviderError, match="HTTP 429"):
        remote.GroqProvider().generate(LLMRequest(task="t", system="s", prompt="p"))

    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(ProviderError, match="network error"):
        remote.GroqProvider().generate(LLMRequest(task="t", system="s", prompt="p"))
