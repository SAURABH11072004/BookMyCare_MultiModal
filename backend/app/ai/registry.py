"""Provider selection with explicit, classified failure handling.

Real providers are tried in ``AI_PROVIDER_ORDER``. Every failure is recorded
with its kind (missing key, rate limit, auth, model not found, timeout, invalid
response...). The template ("mock") provider is only used as the last resort and
only when ``AI_ALLOW_MOCK_FALLBACK`` is true; callers receive an
``availability`` description so mock output can never be presented as real AI.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from app.ai.base import LLMProvider, LLMRequest, LLMResponse, ProviderError
from app.ai.mock import MockProvider
from app.ai.remote import GeminiProvider, GroqProvider, OpenRouterProvider
from app.core.config import get_settings

log = logging.getLogger(__name__)

_FACTORIES: dict[str, type[LLMProvider]] = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "openrouter": OpenRouterProvider,
}


class AllProvidersFailed(RuntimeError):
    """No real provider produced a valid response and mock fallback is off."""

    def __init__(self, attempts: list[dict]):
        super().__init__("No AI provider produced a valid response")
        self.attempts = attempts


def provider_chain(need_vision: bool = False, allow_mock: bool | None = None) -> list[LLMProvider]:
    s = get_settings()
    if allow_mock is None:
        allow_mock = True  # legacy callers (and the status endpoint) always get the mock tail
    chain: list[LLMProvider] = []
    if not s.ai_force_mock:
        for name in s.provider_order:
            cls = _FACTORIES.get(name)
            if cls is None:
                continue
            p = cls()
            if p.available() and (p.supports_vision or not need_vision):
                chain.append(p)
    if allow_mock or s.ai_force_mock:
        chain.append(MockProvider())
    return chain


def availability(need_vision: bool = False) -> dict:
    """Why a real provider is or is not usable right now (no network calls)."""
    s = get_settings()
    if s.ai_force_mock:
        return {"real_configured": False, "reason": "forced_mock",
                "message": "AI_FORCE_MOCK is enabled, so no real AI provider is used."}
    configured = []
    for name in s.provider_order:
        cls = _FACTORIES.get(name)
        if cls is None:
            continue
        p = cls()
        if p.available() and (p.supports_vision or not need_vision):
            configured.append(name)
    if not configured:
        return {"real_configured": False, "reason": "missing_key",
                "message": "No AI provider is configured. Add GEMINI_API_KEY to backend/.env and restart the backend."}
    return {"real_configured": True, "reason": None, "message": "", "providers": configured}


@dataclass
class GenerationOutcome:
    response: LLMResponse
    attempts: list[dict] = field(default_factory=list)

    @property
    def fell_back(self) -> bool:
        return any(a["ok"] is False for a in self.attempts)


def generate(
    req: LLMRequest,
    validate: Callable[[LLMResponse], None] | None = None,
    allow_mock: bool | None = None,
) -> GenerationOutcome:
    """Run ``req`` through the provider chain.

    ``validate`` may raise ``ProviderError(kind="invalid_response")`` to reject a
    provider's reply so the next provider is tried. With ``allow_mock=False`` and
    no valid real response, ``AllProvidersFailed`` is raised instead of returning
    template output.
    """
    if allow_mock is None:
        allow_mock = get_settings().ai_allow_mock_fallback
    attempts: list[dict] = []
    chain = provider_chain(need_vision=bool(req.images))
    if not allow_mock:
        chain = [p for p in chain if not p.is_mock]
    for provider in chain:
        try:
            resp = provider.generate(req)
            if req.json_mode and resp.data is None and not provider.is_mock:
                raise ProviderError("response was not valid JSON", kind="invalid_response")
            if validate is not None:
                validate(resp)
            attempts.append({"provider": provider.name, "ok": True})
            return GenerationOutcome(resp, attempts)
        except ProviderError as exc:
            log.warning("AI provider %s failed (%s): %s", provider.name, exc.kind, exc)
            attempts.append({"provider": provider.name, "ok": False, "kind": exc.kind, "error": str(exc)[:200]})
    if not allow_mock:
        raise AllProvidersFailed(attempts)
    raise RuntimeError("No AI provider available")  # pragma: no cover - mock always succeeds


def status() -> dict:
    s = get_settings()
    configured = []
    for name in s.provider_order:
        cls = _FACTORIES.get(name)
        if cls:
            p = cls()
            configured.append({"name": name, "configured": p.available(), "model": p.model, "vision": p.supports_vision})
    av = availability()
    active = provider_chain()[0]
    return {
        "active_provider": active.name,
        "mock_mode": active.is_mock,
        "force_mock": s.ai_force_mock,
        "allow_mock_fallback": s.ai_allow_mock_fallback,
        "unavailable_reason": av["reason"],
        "unavailable_message": av["message"] or None,
        "providers": configured,
    }
