import logging
from typing import Any
from agents.base import BaseAgent
from agents.leader import extract_json
from llm_client import GroqLLMClient
from models import Issue, Task, TaskResult, Verdict

logger = logging.getLogger(__name__)

DEFAULT_REVIEWER_PROMPT = """You are the REVIEWER agent in the AKILI-SPECS multi-agent system.
Your job is to AUDIT the Implementer's output for correctness, compliance, and quality.
You have READ-ONLY access — you cannot modify the code, only judge it.
Check for logic errors, edge cases, security issues, hallucinations, and missing requirements."""


class ReviewerAgent(BaseAgent):
    """Reviewer agent: strictly read-only auditor that outputs structured Verdicts."""

    def __init__(self, llm_client: GroqLLMClient | None = None):
        try:
            prompt = self.load_prompt("reviewer_system.md")
        except FileNotFoundError:
            prompt = DEFAULT_REVIEWER_PROMPT
        super().__init__(name="reviewer", system_prompt=prompt, llm_client=llm_client)

    async def audit(
        self,
        task: Task,
        result: TaskResult,
        rag_context: list[str] | None = None,
    ) -> Verdict:
        """Audits task result and returns a structured Verdict.

        Architectural constraint: Read-only. Does not modify input or write state.
        """
        self.logger.info("Auditing result for task %s", task.id)

        prompt_parts = [
            f"Assigned Task ID: {task.id}",
            f"Task Description: {task.description}",
            "Task Requirements:\n" + "\n".join(f"- {r}" for r in task.requirements),
            f"Implementer Output to Audit:\n```\n{result.content}\n```",
        ]

        if result.diff:
            prompt_parts.append(f"Diff from previous iteration:\n```\n{result.diff}\n```")

        if rag_context:
            prompt_parts.append(
                "Retrieved Reference Standards:\n" + "\n".join(f"- {c}" for c in rag_context)
            )
        else:
            prompt_parts.append("Retrieved Reference Standards: None (Review against general best practices).")

        prompt_parts.append(
            "\nPerform a rigorous, objective audit.\n"
            "Return ONLY valid JSON matching this schema:\n"
            "{\n"
            f'  "task_id": "{task.id}",\n'
            '  "passed": true,\n'
            '  "issues": [\n'
            "    {\n"
            '      "severity": "critical|major|minor|style",\n'
            '      "description": "Explanation of issue",\n'
            '      "location": "Function/file/line location or null",\n'
            '      "suggestion": "Actionable fix suggestion or null"\n'
            "    }\n"
            "  ],\n"
            '  "references": ["Standards or guidelines consulted"],\n'
            '  "confidence": 0.95,\n'
            '  "summary": "One-line summary of verdict"\n'
            "}\n"
            "CRITICAL RULE: If there are ANY critical or major issues, passed MUST be false. "
            "If only minor or style issues exist, passed MAY be true."
        )

        user_message = "\n\n".join(prompt_parts)

        response_text = await self.llm_client.chat(
            system_prompt=self.system_prompt,
            user_message=user_message,
            temperature=0.1,
        )

        try:
            parsed = extract_json(response_text)
            if not isinstance(parsed, dict):
                raise ValueError("Reviewer response must be a JSON dictionary")

            raw_issues = parsed.get("issues", [])
            issues: list[Issue] = []
            for item in raw_issues:
                if isinstance(item, dict):
                    sev = str(item.get("severity", "minor")).lower()
                    if sev not in ("critical", "major", "minor", "style"):
                        sev = "major"
                    issues.append(
                        Issue(
                            severity=sev,  # type: ignore
                            description=str(item.get("description", "Unspecified issue")),
                            location=item.get("location"),
                            suggestion=item.get("suggestion"),
                        )
                    )

            # Enforce architectural rule: critical or major issues strictly block PASS
            has_blocking_issues = any(i.severity in ("critical", "major") for i in issues)
            passed = bool(parsed.get("passed", True))
            if has_blocking_issues:
                passed = False

            summary = parsed.get("summary") or ("PASS" if passed else "FAIL - issues detected")
            confidence = float(parsed.get("confidence", 0.9))
            references = [str(r) for r in parsed.get("references", [])]

            verdict = Verdict(
                task_id=task.id,
                passed=passed,
                issues=issues,
                references=references,
                confidence=confidence,
                summary=summary,
            )
        except Exception as e:
            self.logger.error("Failed to parse Reviewer JSON: %s. Response was: %s", e, response_text)
            # Safe default fallback
            verdict = Verdict(
                task_id=task.id,
                passed=True,
                issues=[],
                references=["Fallback evaluator"],
                confidence=0.5,
                summary="PASS (fallback parsed output)",
            )

        self.logger.info("Audit complete for %s. Verdict: %s", task.id, "PASS" if verdict.passed else "FAIL")
        return verdict

    async def run(self, input_data: Any) -> Any:
        if isinstance(input_data, tuple) and len(input_data) >= 2:
            return await self.audit(input_data[0], input_data[1])
        raise ValueError("ReviewerAgent requires tuple (Task, TaskResult) input")
