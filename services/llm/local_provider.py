import os
import json
from typing import Any, Dict, List, Optional
import requests
from services.llm.base_provider import LLMProvider


class LocalProvider(LLMProvider):
    """
    OpenAI-compatible local inference provider supporting Ollama and vLLM.
    If local LLM is unreachable or disabled, methods fail gracefully or delegate to fallback.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 15
    ):
        raw_url = base_url or os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434")
        if not raw_url.endswith("/v1") and not raw_url.endswith("/v1/"):
            raw_url = raw_url.rstrip("/") + "/v1"
        self.base_url = raw_url.rstrip("/")
        self.model = model or os.getenv("LOCAL_LLM_MODEL", "qwen3:8b")
        self.timeout = timeout
        self.enabled = os.getenv("LOCAL_LLM_ENABLED", "false").lower() in ("true", "1", "yes")

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            res = requests.get(f"{self.base_url}/models", timeout=3)
            return res.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_reasoning: bool = False
    ) -> str:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as error:
            raise RuntimeError(f"Local LLM call failed ({self.model} at {self.base_url}): {error}")

    def generate_json(
        self,
        prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        use_reasoning: bool = False
    ) -> str:
        json_instruction = "Respond ONLY with valid JSON conforming to the requested schema. Do not output markdown code fences or conversational prose."
        combined_sys = f"{system_instruction}\n{json_instruction}" if system_instruction else json_instruction
        if schema:
            prompt = f"{prompt}\n\nRequired JSON Schema:\n{json.dumps(schema, indent=2)}"

        res = self.generate(
            prompt=prompt,
            system_instruction=combined_sys,
            temperature=temperature,
            use_reasoning=use_reasoning
        )
        clean = res.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        return clean.strip()

    def embed(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        target_model = model or self.model
        try:
            resp = requests.post(
                f"{self.base_url}/embeddings",
                json={"model": target_model, "input": texts},
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]
        except Exception as error:
            raise RuntimeError(f"Local LLM embeddings failed: {error}")

    def health_check(self) -> Dict[str, Any]:
        try:
            available = self.is_available()
            return {
                "status": "healthy" if available else "offline",
                "provider": "local",
                "model": self.model,
                "base_url": self.base_url,
                "enabled": self.enabled
            }
        except Exception as e:
            return {"status": "unhealthy", "provider": "local", "error": str(e)}
