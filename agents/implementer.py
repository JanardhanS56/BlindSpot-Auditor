import difflib
import logging
from typing import Any
from agents.base import BaseAgent
from agents.leader import extract_json
from llm_client import GroqLLMClient
from models import Task, TaskResult

logger = logging.getLogger(__name__)

DEFAULT_IMPLEMENTER_PROMPT = """You are an IMPLEMENTER agent in the AKILI-SPECS multi-agent system.
Your job is to PRODUCE high-quality code, content, or solutions for the specific sub-task assigned to you.
Work only on the assigned sub-task and include type hints, error handling, and docstrings in all code.
If given reviewer_notes from a previous review, address each noted issue explicitly."""


class ImplementerAgent(BaseAgent):
    """Implementer agent: generates code or content for a specific task."""

    def __init__(self, llm_client: GroqLLMClient | None = None):
        try:
            prompt = self.load_prompt("implementer_system.md")
        except FileNotFoundError:
            prompt = DEFAULT_IMPLEMENTER_PROMPT
        super().__init__(name="implementer", system_prompt=prompt, llm_client=llm_client)
        self._history: dict[str, list[str]] = {}

    async def generate(self, task: Task) -> TaskResult:
        """Generates code or technical content for the given task."""
        self.logger.info("Generating for task %s (attempt %d)", task.id, task.attempt)

        prompt_parts = [
            f"Assigned Task ID: {task.id}",
            f"Description: {task.description}",
            f"Requirements:\n" + "\n".join(f"- {r}" for r in task.requirements),
        ]

        if task.context:
            prompt_parts.append(f"Context: {task.context}")

        if task.reviewer_notes:
            prompt_parts.append(
                f"REVIEWER FEEDBACK FROM PREVIOUS ATTEMPT (MUST BE ADDRESSED):\n{task.reviewer_notes}"
            )

        prompt_parts.append(
            "\nProduce the complete implementation or solution.\n"
            "Return a JSON object matching this schema:\n"
            "{\n"
            f'  "task_id": "{task.id}",\n'
            '  "content": "Complete code or text implementation",\n'
            '  "approach": "Brief summary of approach",\n'
            '  "assumptions": ["List of assumptions"],\n'
            '  "changes_from_previous": "Summary of fixes if this is a retry"\n'
            "}"
        )

        user_message = "\n\n".join(prompt_parts)

        response_text = await self.llm_client.chat(
            system_prompt=self.system_prompt,
            user_message=user_message,
            temperature=0.2,
        )

        content = response_text
        metadata: dict[str, Any] = {
            "attempt": task.attempt,
            "llm_meta": self.llm_client.last_metadata,
        }

        try:
            parsed = extract_json(response_text)
            if isinstance(parsed, dict) and "content" in parsed:
                content = parsed["content"]
                if "approach" in parsed:
                    metadata["approach"] = parsed["approach"]
                if "assumptions" in parsed:
                    metadata["assumptions"] = parsed["assumptions"]
                if "changes_from_previous" in parsed:
                    metadata["changes_from_previous"] = parsed["changes_from_previous"]
        except Exception:
            # Response was directly markdown or code, keep content as response_text
            content = response_text.strip()

        # Compute diff if prior attempt existed
        diff_str: str | None = None
        prior_versions = self._history.setdefault(task.id, [])
        if prior_versions:
            last_content = prior_versions[-1]
            diff_lines = list(
                difflib.unified_diff(
                    last_content.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=f"{task.id}_v{task.attempt - 1}",
                    tofile=f"{task.id}_v{task.attempt}",
                )
            )
            if diff_lines:
                diff_str = "".join(diff_lines)

        prior_versions.append(content)

        return TaskResult(
            task_id=task.id,
            content=content,
            diff=diff_str,
            metadata=metadata,
        )

    async def run(self, input_data: Any) -> Any:
        if isinstance(input_data, Task):
            return await self.generate(input_data)
        raise ValueError(f"ImplementerAgent requires Task input, got {type(input_data)}")
