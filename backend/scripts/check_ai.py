"""Check the configured AI providers with one tiny live request each.

    python -m scripts.check_ai

Prints, per provider, whether the key is configured and whether a real call
succeeded, or the classified failure (rate_limited, auth_error, model_not_found,
timeout, invalid_response ...). API keys are never printed.
Exit code: 0 = at least one provider answered, 1 = configured but all failed, 2 = none configured.
"""
from __future__ import annotations

import sys

from app.ai import registry
from app.ai.base import LLMRequest, ProviderError
from app.core.config import get_settings
from app.services.grounding import KIND_MESSAGES


def main() -> int:
    s = get_settings()
    print(f"AI_PROVIDER_ORDER={s.ai_provider_order}  AI_FORCE_MOCK={s.ai_force_mock}  AI_ALLOW_MOCK_FALLBACK={s.ai_allow_mock_fallback}")
    av = registry.availability()
    if not av["real_configured"]:
        print(f"No real provider is usable: {av['message']}")
        return 2
    ok = False
    for name in av["providers"]:
        p = registry._FACTORIES[name]()
        req = LLMRequest(task="check", system="Reply with a JSON object only.", prompt='Return {"ok": true}.', max_tokens=256)
        try:
            resp = p.generate(req)
            good = isinstance(resp.data, dict)
            print(f"[{'OK' if good else 'FAIL'}] {name} ({p.model}): " + ("answered with valid JSON" if good else "answered but not valid JSON (invalid_response)"))
            ok = ok or good
        except ProviderError as exc:
            print(f"[FAIL] {name} ({p.model}): {exc.kind} - {KIND_MESSAGES.get(exc.kind, '')} [{str(exc)[:160]}]")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
