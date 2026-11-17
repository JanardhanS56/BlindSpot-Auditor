import json
import logging
import re
from typing import Any
from agents.base import BaseAgent
from llm_client import GroqLLMClient
from models import AggregateReport, Task, TaskResult

logger = logging.getLogger(__name__)

DEFAULT_LEADER_PROMPT = """You are the LEADER agent in the AKILI-SPECS multi-agent system.
Your job is to PLAN and COORDINATE — never to write code or content yourself.
You decompose user prompts into structured sub-tasks with clear acceptance criteria.
You also merge completed sub-task results into a unified final answer."""


def extract_json(text: str) -> dict | list:
    """Extracts and parses JSON object or array from markdown or raw text."""
    text = text.strip()
    # Check for markdown code blocks
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try finding first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        # If truncated inside tasks list, attempt recovery by closing the array at the last valid task
        if '"tasks"' in text:
            last_brace = text.rfind("}")
            if last_brace != -1:
                candidate = text[: last_brace + 1].strip()
                if not candidate.endswith("]"):
                    candidate += "\n  ]"
                if not candidate.endswith("}"):
                    candidate += "\n}"
                try:
                    return json.loads(candidate)
                except Exception:
                    pass
        raise


class LeaderAgent(BaseAgent):
    """Leader agent: decomposes prompts into tasks and merges completed task results."""

    def __init__(self, llm_client: GroqLLMClient | None = None):
        try:
            prompt = self.load_prompt("leader_system.md")
        except FileNotFoundError:
            prompt = DEFAULT_LEADER_PROMPT
        super().__init__(name="leader", system_prompt=prompt, llm_client=llm_client)

    async def decompose(self, prompt: str) -> list[Task]:
        """Decomposes a user prompt into structured Task objects."""
        self.logger.info("Decomposing prompt: %s", prompt[:80])
        user_message = (
            f"User Prompt:\n{prompt}\n\n"
            "Decompose this prompt into independent sub-tasks.\n"
            "Return ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "analysis": "Brief analysis",\n'
            '  "tasks": [\n'
            "    {\n"
            '      "id": "task-1",\n'
            '      "description": "What to produce",\n'
            '      "requirements": ["Criterion 1", "Criterion 2"],\n'
            '      "context": "Context needed",\n'
            '      "priority": 1\n'
            "    }\n"
            "  ],\n"
            '  "merge_strategy": "How to combine results"\n'
            "}"
        )

        response_text = await self.llm_client.chat(
            system_prompt=self.system_prompt,
            user_message=user_message,
            temperature=0.2,
        )

        try:
            data = extract_json(response_text)
            raw_tasks = data.get("tasks", []) if isinstance(data, dict) else data
        except Exception as e:
            self.logger.error("Failed to parse JSON decomposition: %s. Response was: %s", e, response_text)
            # Fallback single task
            raw_tasks = [
                {
                    "id": "task-1",
                    "description": prompt,
                    "requirements": ["Fulfill user request completely"],
                    "context": None,
                    "priority": 1,
                }
            ]

        tasks: list[Task] = []
        for idx, item in enumerate(raw_tasks, start=1):
            task_id = item.get("id") or f"task-{idx}"
            desc = item.get("description") or prompt
            reqs = item.get("requirements") or ["Produce complete implementation"]
            ctx = item.get("context")
            priority = item.get("priority", idx)
            tasks.append(
                Task(
                    id=str(task_id),
                    description=desc,
                    requirements=reqs if isinstance(reqs, list) else [str(reqs)],
                    context=ctx,
                    priority=priority,
                )
            )

        self.logger.info("Decomposed into %d tasks.", len(tasks))
        return tasks

    async def merge(
        self,
        results: list[TaskResult],
        warnings: list[str] | None = None,
        report: AggregateReport | None = None,
    ) -> str:
        """Merges all task results into a coherent final answer."""
        warn_count = len(warnings or [])
        report_summary = ""
        if report:
            warn_count = len(report.unresolved_warnings) or warn_count
            report_summary = (
                f"\nExecution Report: Total={report.total_tasks}, Passed={report.passed}, "
                f"Retried-then-passed={report.failed_then_passed}, Force-merged={report.force_merged}, "
                f"Issues Resolved={report.issues_resolved}/{report.total_issues_found}\n"
            )

        self.logger.info("Merging %d results with %d warnings.", len(results), warn_count)

        formatted_results = []
        for r in results:
            formatted_results.append(
                f"### Task {r.task_id} Output:\n{r.content}\n"
            )
        all_results_str = "\n".join(formatted_results)

        active_warnings = warnings or (report.unresolved_warnings if report else [])
        warnings_str = ""
        if active_warnings:
            warnings_str = (
                "\n### ⚠ Unresolved Concerns (from Reviewer audits):\n"
                + "\n".join(f"- {w}" for w in active_warnings)
            )

        user_message = (
            "Combine the following sub-task outputs into a single, cohesive, unified response.\n"
            "Eliminate redundancy between sub-task outputs, preserve all important details, "
            "and ensure proper flow.\n\n"
            f"{report_summary}"
            f"{all_results_str}\n"
            f"{warnings_str}\n\n"
            "Instructions:\n"
            "1. Produce a complete, unified answer that addresses the full user intent.\n"
            "2. If '⚠ Unresolved Concerns' are present above, you MUST include a dedicated "
            "'## ⚠ Unresolved Concerns' section at the end highlighting these caveats clearly.\n"
            "3. If no unresolved concerns exist, do not fabricate warnings."
        )

        final_answer = await self.llm_client.chat(
            system_prompt=self.system_prompt,
            user_message=user_message,
            temperature=0.2,
        )

        return final_answer.strip()

    async def run(self, input_data: Any) -> Any:
        if isinstance(input_data, str):
            return await self.decompose(input_data)
        elif isinstance(input_data, list):
            return await self.merge(input_data)
        raise ValueError(f"Unsupported input type for LeaderAgent: {type(input_data)}")
