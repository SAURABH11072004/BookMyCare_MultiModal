"""Provider selection with automatic fallback to the mock provider."""
from __future__ import annotations

import logging
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


def provider_chain(need_vision: bool = False) -> list[LLMProvider]:
    s = get_settings()
    chain: list[LLMProvider] = []
    if not s.ai_force_mock:
        for name in s.provider_order:
            cls = _FACTORIES.get(name)
            if cls is None:
                continue
            p = cls()
            if p.available() and (p.supports_vision or not need_vision):
                chain.append(p)
    chain.append(MockProvider())
    return chain


@dataclass
class GenerationOutcome:
    response: LLMResponse
    attempts: list[dict] = field(default_factory=list)

    @property
    def fell_back(self) -> bool:
        return any(a["ok"] is False for a in self.attempts)


def generate(req: LLMRequest) -> GenerationOutcome:
    attempts: list[dict] = []
    for provider in provider_chain(need_vision=bool(req.images)):
        try:
            resp = provider.generate(req)
            if req.json_mode and resp.data is None and not provider.is_mock:
                raise ProviderError("response was not valid JSON")
            attempts.append({"provider": provider.name, "ok": True})
            return GenerationOutcome(resp, attempts)
        except ProviderError as exc:
            log.warning("AI provider %s failed: %s", provider.name, exc)
            attempts.append({"provider": provider.name, "ok": False, "error": str(exc)[:200]})
    raise RuntimeError("No AI provider available")  # pragma: no cover - mock always succeeds


def status() -> dict:
    s = get_settings()
    configured = []
    for name in s.provider_order:
        cls = _FACTORIES.get(name)
        if cls:
            p = cls()
            configured.append({"name": name, "configured": p.available(), "model": p.model, "vision": p.supports_vision})
    active = provider_chain()[0]
    return {
        "active_provider": active.name,
        "mock_mode": active.is_mock,
        "force_mock": s.ai_force_mock,
        "providers": configured,
    }
