from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):

    @abstractmethod
    def generate_json(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        *,
        temperature: float = 0.2,
        max_output_tokens: int = 4096,
        images: list | None = None,
    ) -> dict:
        pass