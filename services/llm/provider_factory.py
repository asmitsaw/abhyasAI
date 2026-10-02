import os
from typing import Any, Dict, List, Optional
from services.llm.base_provider import LLMProvider
from services.llm.gemini_provider import GeminiProvider
from services.llm.local_provider import LocalProvider


class AutoFallbackProvider(LLMProvider):
    """
    Orchestrates automatic fallback between Gemini and Local LLM.
    If local is preferred and available, uses local; otherwise falls back to Gemini.
    If Gemini fails with high demand and local is available, falls back to local.
    """

    def __init__(self, primary: LLMProvider, fallback: LLMProvider):
        self.primary = primary
        self.fallback = fallback

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_reasoning: bool = False
    ) -> str:
        try:
            return self.primary.generate(prompt, system_instruction, temperature, max_tokens, use_reasoning)
        except Exception as primary_error:
            print(f"[LLM AutoFallback] Primary provider failed ({primary_error}). Attempting fallback...")
            return self.fallback.generate(prompt, system_instruction, temperature, max_tokens, use_reasoning)

    def generate_json(
        self,
        prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        use_reasoning: bool = False
    ) -> str:
        try:
            return self.primary.generate_json(prompt, schema, system_instruction, temperature, use_reasoning)
        except Exception as primary_error:
            print(f"[LLM AutoFallback] Primary JSON generation failed ({primary_error}). Attempting fallback...")
            return self.fallback.generate_json(prompt, schema, system_instruction, temperature, use_reasoning)

    def embed(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        try:
            return self.primary.embed(texts, model)
        except Exception as primary_error:
            print(f"[LLM AutoFallback] Primary embedding failed ({primary_error}). Attempting fallback...")
            return self.fallback.embed(texts, model)

    def health_check(self) -> Dict[str, Any]:
        p_health = self.primary.health_check()
        f_health = self.fallback.health_check()
        return {
            "mode": "auto",
            "primary": p_health,
            "fallback": f_health,
            "status": "healthy" if p_health.get("status") == "healthy" or f_health.get("status") == "healthy" else "unhealthy"
        }


_cached_provider: Optional[LLMProvider] = None


def get_llm_provider(force_provider: Optional[str] = None) -> LLMProvider:
    """
    Factory function returning the configured LLMProvider singleton.
    Reads LLM_PROVIDER ('gemini', 'local', 'auto').
    """
    global _cached_provider
    if _cached_provider is not None and force_provider is None:
        return _cached_provider

    provider_name = (force_provider or os.getenv("LLM_PROVIDER", "gemini")).lower()

    if provider_name == "local":
        local_p = LocalProvider()
        if local_p.is_available():
            provider = local_p
        else:
            print("[ProviderFactory] Local LLM requested but unavailable. Falling back to Gemini.")
            provider = GeminiProvider()
    elif provider_name == "auto":
        gemini_p = GeminiProvider()
        local_p = LocalProvider()
        # Primary is Gemini, fallback is Local if available, else Gemini itself
        provider = AutoFallbackProvider(primary=gemini_p, fallback=local_p if local_p.is_available() else gemini_p)
    else:
        # Default: Gemini
        provider = GeminiProvider()

    if force_provider is None:
        _cached_provider = provider
    return provider


def reset_provider_cache():
    global _cached_provider
    _cached_provider = None
