import asyncio
import pytest
from agents.implementer import ImplementerAgent
from agents.leader import LeaderAgent
from agents.reviewer import ReviewerAgent
from models import Issue, Task, TaskResult, Verdict
from orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_leader_decomposition():
    """Verify Leader decomposes prompt into structured tasks."""
    leader = LeaderAgent()
    tasks = await leader.decompose("Build a REST API for a todo app with authentication and database models")
    assert len(tasks) >= 3, f"Expected at least 3 tasks, got {len(tasks)}"
    for task in tasks:
        assert task.id
        assert task.description
        assert len(task.requirements) > 0


@pytest.mark.asyncio
async def test_implementer_and_reviewer():
    """Verify Implementer generates code and Reviewer produces a valid Verdict."""
    implementer = ImplementerAgent()
    reviewer = ReviewerAgent()

    task = Task(
        id="task-smoke-1",
        description="Write a Python function named `greet` that takes a name: str and returns a greeting string.",
        requirements=[
            "Function name must be `greet`",
            "Must accept `name: str` parameter",
            "Must include docstring and type hints",
        ],
    )

    result = await implementer.generate(task)
    assert result.content
    assert "greet" in result.content

    verdict = await reviewer.audit(task, result)
    assert isinstance(verdict, Verdict)
    assert verdict.task_id == task.id
    assert isinstance(verdict.passed, bool)
    assert verdict.summary


@pytest.mark.asyncio
async def test_feedback_loop_and_force_merge(monkeypatch):
    """Verify retry loop injects reviewer notes and handles max retries force-merge."""
    leader = LeaderAgent()
    implementer = ImplementerAgent()
    reviewer = ReviewerAgent()

    # Mock reviewer to always fail with a critical issue to test retry & force-merge
    audit_calls = []

    async def mock_failing_audit(task: Task, result: TaskResult, rag_context=None) -> Verdict:
        audit_calls.append((task.attempt, task.reviewer_notes))
        return Verdict(
            task_id=task.id,
            passed=False,
            issues=[
                Issue(
                    severity="critical",
                    description="Simulated critical failure for test",
                    location="line 1",
                    suggestion="Fix the simulated bug",
                )
            ],
            references=["Mock Standard"],
            confidence=1.0,
            summary="FAIL - Simulated critical error",
        )

    monkeypatch.setattr(reviewer, "audit", mock_failing_audit)

    orchestrator = Orchestrator(
        leader=leader,
        implementer=implementer,
        reviewer=reviewer,
        max_retries=3,
    )

    final = await orchestrator.run("Write a tiny function that returns 42")
    assert len(audit_calls) == 3, f"Expected 3 audit attempts, got {len(audit_calls)}"
    # Verify reviewer notes were injected on subsequent attempts
    assert audit_calls[0][1] is None  # first attempt has no notes
    assert audit_calls[1][1] is not None  # second attempt has notes injected
    assert "Simulated critical error" in audit_calls[1][1]
    assert final


@pytest.mark.asyncio
async def test_full_pipeline_smoke():
    """Verify full end-to-end pipeline execution from prompt to merged response."""
    orchestrator = Orchestrator()
    prompt = "Write a hello world function in Python"
    response = await orchestrator.run(prompt)

    assert response, "Response must not be empty"
    assert "def " in response or "hello" in response.lower(), "Response must contain a function definition or greeting"
    
    stages = [entry["stage"] for entry in orchestrator.execution_log]
    assert "decompose" in stages, "Leader decompose stage was not executed"
    assert "audit" in stages, "Reviewer audit stage was not executed"
    assert "merge" in stages, "Leader merge stage was not executed"
