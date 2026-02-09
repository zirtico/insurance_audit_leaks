"""
Minimal LLM provider abstraction with a free/local default.

If ollama is installed locally, this can call it via subprocess.
Otherwise it falls back to deterministic, template-driven output.
"""

from dataclasses import dataclass
from typing import Optional
import json
import shutil
import subprocess


@dataclass
class LLMResponse:
    content: str
    model: str
    used_fallback: bool = False


class BaseLLMProvider:
    def generate(self, prompt: str) -> LLMResponse:
        raise NotImplementedError


class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: str = "llama3.1"):
        self.model = model

    def generate(self, prompt: str) -> LLMResponse:
        if not shutil.which("ollama"):
            return LLMResponse(
                content="",
                model=self.model,
                used_fallback=True
            )

        payload = {"model": self.model, "prompt": prompt, "stream": False}
        result = subprocess.run(
            ["ollama", "run", self.model],
            input=prompt,
            text=True,
            capture_output=True,
            check=False
        )
        content = result.stdout.strip()
        if not content:
            return LLMResponse(content="", model=self.model, used_fallback=True)
        return LLMResponse(content=content, model=self.model)


class FallbackProvider(BaseLLMProvider):
    def __init__(self, model: str = "template"):
        self.model = model

    def generate(self, prompt: str) -> LLMResponse:
        return LLMResponse(content="", model=self.model, used_fallback=True)


def default_provider() -> BaseLLMProvider:
    if shutil.which("ollama"):
        return OllamaProvider()
    return FallbackProvider()
