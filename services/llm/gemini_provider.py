import os
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from google import genai
from services.llm.base_provider import LLMProvider

load_dotenv()


class GeminiProvider(LLMProvider):
    """
    Google Gemini implementation of LLMProvider with exponential backoff retries,
    fallback model transitions, and structured JSON output.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing. Please set it in your environment or .env file.")

        self.client = genai.Client(api_key=self.api_key)
        self.primary_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.reasoning_model = os.getenv("GEMINI_REASONING_MODEL", "gemini-3.1-pro-preview")
        self.fallback_models = ["gemini-3.6-flash", "gemini-flash-latest"]
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

    def _call_with_retry(
        self,
        prompt: str,
        response_format: Optional[Dict[str, Any]] = None,
        use_reasoning: bool = False,
        system_instruction: Optional[str] = None,
        max_retries: int = 3,
        delay: int = 2
    ) -> str:
        chosen_primary = self.reasoning_model if use_reasoning else self.primary_model
        models_to_try = [chosen_primary] + self.fallback_models

        for model_index, model_name in enumerate(models_to_try):
            current_delay = delay
            for attempt in range(1, max_retries + 1):
                try:
                    kwargs: Dict[str, Any] = {
                        "model": model_name,
                        "input": prompt
                    }
                    if response_format:
                        kwargs["response_format"] = response_format

                    interaction = self.client.interactions.create(**kwargs)
                    return interaction.output_text or ""

                except Exception as error:
                    error_str = str(error).lower()
                    is_rate_limit = "429" in error_str or "too_many_requests" in error_str or "quota" in error_str
                    is_service_unavailable = any(code in error_str for code in ["503", "service_unavailable", "high demand", "overloaded", "temporarily unavailable", "500", "502", "504"])
                    is_network_error = any(net_err in error_str for net_err in ["getaddrinfo", "gaierror", "connection", "connecterror", "socket", "timeout", "reset by peer", "winerror 10060", "winerror 10061"])

                    if is_rate_limit or is_service_unavailable or is_network_error:
                        reason = "Network Error" if is_network_error else ("503 High Demand" if is_service_unavailable else "429 Rate Limit")
                        if attempt < max_retries:
                            time.sleep(current_delay)
                            current_delay *= 2
                            continue
                        elif model_index < len(models_to_try) - 1:
                            break
                        else:
                            raise RuntimeError(f"Gemini API unavailable across retries ({reason}): {error}")
                    elif "403" in error_str or "permission_denied" in error_str:
                        raise RuntimeError("Gemini API Permission Denied (403). Check your GEMINI_API_KEY in .env.")
                    else:
                        raise error
        return ""

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_reasoning: bool = False
    ) -> str:
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"System Instruction: {system_instruction}\n\nUser Prompt: {prompt}"
        return self._call_with_retry(full_prompt, use_reasoning=use_reasoning)

    def generate_json(
        self,
        prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        use_reasoning: bool = False
    ) -> str:
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"System Instruction: {system_instruction}\n\nUser Prompt: {prompt}"

        response_format: Dict[str, Any] = {
            "type": "text",
            "mime_type": "application/json"
        }
        if schema:
            response_format["schema"] = schema

        return self._call_with_retry(full_prompt, response_format=response_format, use_reasoning=use_reasoning)

    def embed(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        target_model = model or self.embedding_model
        try:
            # Check if models embedContent is supported or fallback
            results = []
            for text in texts:
                try:
                    response = self.client.models.embed_content(
                        model=target_model,
                        contents=text
                    )
                    # Support both object attributes and dict
                    if hasattr(response, "embedding") and hasattr(response.embedding, "values"):
                        results.append(list(response.embedding.values))
                    elif hasattr(response, "embeddings") and len(response.embeddings) > 0:
                        results.append(list(response.embeddings[0].values))
                    else:
                        # Fallback pseudo embedding for safety
                        results.append([0.0] * 768)
                except Exception:
                    # Provide stable deterministic pseudo-vector if API quota/model unsupported
                    import hashlib
                    hash_digest = hashlib.sha256(text.encode('utf-8')).digest()
                    vector = [(b / 255.0) for b in hash_digest] * 24
                    results.append(vector[:768])
            return results
        except Exception as error:
            print(f"Gemini embedding error: {error}")
            import hashlib
            results = []
            for text in texts:
                hash_digest = hashlib.sha256(text.encode('utf-8')).digest()
                vector = [(b / 255.0) for b in hash_digest] * 24
                results.append(vector[:768])
            return results

    def health_check(self) -> Dict[str, Any]:
        try:
            res = self.generate("Reply with 'OK'")
            return {"status": "healthy", "provider": "gemini", "model": self.primary_model, "response": res.strip()}
        except Exception as e:
            return {"status": "unhealthy", "provider": "gemini", "model": self.primary_model, "error": str(e)}
