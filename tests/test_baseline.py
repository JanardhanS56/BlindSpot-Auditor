import asyncio
import pytest
from pydantic import BaseModel, Field
from config import DEFAULT_MODEL
from llm_client import GroqLLMClient, default_llm_client
from orchestrator import Orchestrator


class ComparisonResult(BaseModel):
    prompt: str
    baseline_output: str
    triad_output: str
    baseline_tokens: int = 0
    triad_execution_log: list[dict] = Field(default_factory=list)


class SingleAgentBaseline:
    """Single-agent baseline: direct LLM call with no decomposition or review."""

    def __init__(
        self,
        llm_client: GroqLLMClient | None = None,
        model: str | None = None,
        temperature: float = 0.2,
    ):
        self.llm_client = llm_client or default_llm_client
        self.model = model or DEFAULT_MODEL
        self.temperature = temperature
        self.system_prompt = "You are a helpful assistant."

    async def run(self, prompt: str) -> str:
        """Runs the single-agent baseline directly against Groq."""
        return await self.llm_client.chat(
            system_prompt=self.system_prompt,
            user_message=prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=1500,
        )

    async def compare(
        self,
        prompt: str,
        orchestrator: Orchestrator | None = None,
    ) -> ComparisonResult:
        """Runs both baseline and AKILI-SPECS triad on the same prompt."""
        orch = orchestrator or Orchestrator()
        baseline_out = await self.run(prompt)
        triad_out = await orch.run(prompt)

        baseline_tokens = self.llm_client.last_metadata.get("total_tokens", 0)

        return ComparisonResult(
            prompt=prompt,
            baseline_output=baseline_out,
            triad_output=triad_out,
            baseline_tokens=baseline_tokens,
            triad_execution_log=list(orch.execution_log),
        )


@pytest.mark.asyncio
async def test_baseline_instantiation():
    """Verify single-agent baseline config matches triad models and parameters."""
    baseline = SingleAgentBaseline()
    assert baseline.model == DEFAULT_MODEL
    assert baseline.temperature == 0.2
    assert baseline.system_prompt == "You are a helpful assistant."
