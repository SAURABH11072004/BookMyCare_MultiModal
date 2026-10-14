"""HTTP providers: Google Gemini and OpenAI-compatible APIs (Groq, OpenRouter)."""
from __future__ import annotations

import base64

import httpx

from app.ai.base import LLMProvider, LLMRequest, ProviderError
from app.core.config import get_settings


def _post(url: str, headers: dict, payload: dict) -> dict:
    s = get_settings()
    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=s.ai_timeout_seconds)
    except httpx.HTTPError as exc:
        raise ProviderError(f"network error: {exc.__class__.__name__}") from exc
    if r.status_code >= 400:
        # Never echo request headers (they contain the key); body text is truncated.
        raise ProviderError(f"HTTP {r.status_code}: {r.text[:300]}")
    try:
        return r.json()
    except ValueError as exc:
        raise ProviderError("invalid JSON response") from exc


class GeminiProvider(LLMProvider):
    name = "gemini"
    supports_vision = True

    def available(self) -> bool:
        return bool(get_settings().gemini_api_key)

    @property
    def model(self) -> str:
        return get_settings().gemini_model

    def _generate(self, req: LLMRequest) -> str:
        s = get_settings()
        parts: list[dict] = [{"text": req.prompt}]
        for img in req.images:
            parts.append({"inline_data": {"mime_type": img.mime_type, "data": base64.b64encode(img.data).decode()}})
        gen_cfg: dict = {"temperature": req.temperature, "maxOutputTokens": req.max_tokens}
        if req.json_mode:
            gen_cfg["responseMimeType"] = "application/json"
        payload = {
            "systemInstruction": {"parts": [{"text": req.system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": gen_cfg,
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{s.gemini_model}:generateContent"
        data = _post(url, {"x-goog-api-key": s.gemini_api_key, "Content-Type": "application/json"}, payload)
        try:
            cand = data["candidates"][0]
            return "".join(p.get("text", "") for p in cand["content"]["parts"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            reason = (data.get("promptFeedback") or {}).get("blockReason") if isinstance(data, dict) else None
            raise ProviderError(f"unexpected Gemini response{f' (blocked: {reason})' if reason else ''}") from exc


class OpenAICompatibleProvider(LLMProvider):
    base_url: str = ""

    def _key(self) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    def available(self) -> bool:
        return bool(self._key())

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._key()}", "Content-Type": "application/json"}

    def _generate(self, req: LLMRequest) -> str:
        payload: dict = {
            "model": self.model,
            "messages": [{"role": "system", "content": req.system}, {"role": "user", "content": req.prompt}],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        if req.json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = _post(f"{self.base_url}/chat/completions", self._headers(), payload)
        try:
            return (data["choices"][0]["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"unexpected {self.name} response") from exc


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"
    base_url = "https://api.groq.com/openai/v1"

    def _key(self) -> str:
        return get_settings().groq_api_key

    @property
    def model(self) -> str:
        return get_settings().groq_model


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"

    def _key(self) -> str:
        return get_settings().openrouter_api_key

    @property
    def model(self) -> str:
        return get_settings().openrouter_model

    def _headers(self) -> dict:
        h = super()._headers()
        h["X-Title"] = "BookMyCare"
        return h
