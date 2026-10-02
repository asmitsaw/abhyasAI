from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class LLMProvider(ABC):
    """
    Abstract base interface for all LLM providers (Gemini, Local/Ollama/vLLM, etc.).
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        use_reasoning: bool = False
    ) -> str:
        """
        Generate plain text response for given prompt.
        """
        pass

    @abstractmethod
    def generate_json(
        self,
        prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        use_reasoning: bool = False
    ) -> str:
        """
        Generate structured JSON string conforming to optional schema.
        """
        pass

    @abstractmethod
    def embed(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """
        Generate vector embeddings for a list of text strings.
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Verify if the provider and its target model are reachable and functional.
        """
        pass
