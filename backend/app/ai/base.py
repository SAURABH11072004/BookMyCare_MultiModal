"""Common interface for text/vision generation providers."""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ProviderError(RuntimeError):
    pass


@dataclass
class ImageInput:
    mime_type: str
    data: bytes


@dataclass
class LLMRequest:
    task: str  # e.g. "analysis_explanation", "image_observation"
    system: str
    prompt: str
    images: list[ImageInput] = field(default_factory=list)
    json_mode: bool = True
    temperature: float = 0.2
    max_tokens: int = 1200
    # Structured context, used by the mock provider to produce templated output.
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    is_mock: bool = False
    data: dict[str, Any] | None = None  # parsed JSON if json_mode


class LLMProvider(ABC):
    name: str = "base"
    is_mock: bool = False
    supports_vision: bool = False

    @abstractmethod
    def available(self) -> bool: ...

    @property
    @abstractmethod
    def model(self) -> str: ...

    @abstractmethod
    def _generate(self, req: LLMRequest) -> str: ...

    def generate(self, req: LLMRequest) -> LLMResponse:
        if req.images and not self.supports_vision:
            raise ProviderError(f"{self.name} does not support image input")
        text = self._generate(req)
        data = parse_json_loose(text) if req.json_mode else None
        return LLMResponse(text=text, provider=self.name, model=self.model, is_mock=self.is_mock, data=data)


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.M)


def parse_json_loose(text: str) -> dict[str, Any] | None:
    """Parse a JSON object from model output, tolerating code fences or
    surrounding prose."""
    if not text:
        return None
    t = _FENCE.sub("", text.strip())
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(t[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None
