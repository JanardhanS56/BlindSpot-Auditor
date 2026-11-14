from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Any
from llm_client import GroqLLMClient, default_llm_client

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all AKILI-SPECS agents."""

    def __init__(
        self,
        name: str,
        prompt_file: str | None = None,
        system_prompt: str | None = None,
        llm_client: GroqLLMClient | None = None,
    ):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
        self.llm_client = llm_client or default_llm_client

        if system_prompt is not None:
            self.system_prompt = system_prompt
        elif prompt_file is not None:
            self.system_prompt = self.load_prompt(prompt_file)
        else:
            self.system_prompt = ""

    @staticmethod
    def load_prompt(prompt_filename: str) -> str:
        """Loads a markdown prompt from the prompts directory."""
        base_dir = Path(__file__).resolve().parent.parent / "prompts"
        prompt_path = base_dir / prompt_filename
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    @abstractmethod
    async def run(self, input_data: Any) -> Any:
        """Abstract execution method for agent."""
        pass
