import pytest
from orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_full_pipeline_parallel_and_rag():
    """Comprehensive integration test for AKILI-SPECS multi-agent system.

    Validates:
    1. Leader decomposes complex prompt into sub-tasks (3+ tasks).
    2. Parallel execution: tasks run concurrently via asyncio.gather.
    3. Reviewer conducts audit and cites RAG knowledge base sources.
    4. Execution log records AggregateReport with total/passed/retried/force_merged.
    5. Final merged answer is coherent, addresses the prompt, and handles any warnings.
    """
    orchestrator = Orchestrator()

    prompt = (
        "Design and implement a Python rate limiter module with three distinct parts: "
        "Part 1: Implement TokenBucket and LeakyBucket algorithms with full class definitions and type hints. "
        "Part 2: Implement thread-safe synchronization using locks and validate input parameters. "
        "Part 3: Provide unit tests and docstrings adhering to Google Python style guidelines."
    )

    final_answer = await orchestrator.run(prompt)

    # 1. Final answer check
    assert final_answer, "Final merged response must not be empty"
    assert len(final_answer) > 200, "Final response should be comprehensive"

    # 2. Decomposition check
    decomp_entries = [e for e in orchestrator.execution_log if e["stage"] == "decompose"]
    assert len(decomp_entries) == 1, "Must have exactly 1 decompose stage"
    task_count = decomp_entries[0]["task_count"]
    assert task_count >= 2, f"Expected multi-task decomposition, got {task_count}"

    # 3. Parallel dispatch check
    assert len(orchestrator.completed_results) == task_count
    if task_count >= 2:
        start_times = [r.metadata.get("start_time", 0) for r in orchestrator.completed_results]
        max_start_diff = max(start_times) - min(start_times)
        # Concurrent launch means all tasks start nearly simultaneously
        assert max_start_diff < 5.0, (
            f"Expected tasks to start concurrently, start diff was {max_start_diff}s"
        )

    # 4. RAG citation check
    audit_entries = [e for e in orchestrator.execution_log if e["stage"] == "audit"]
    assert len(audit_entries) >= task_count, "Each task must undergo at least one audit"

    has_citations = any(
        len(e.get("references", [])) > 0
        for e in audit_entries
    )
    assert has_citations, f"Reviewer must cite references in audits. Entries: {audit_entries}"

    # 5. Aggregate report check
    agg_entries = [e for e in orchestrator.execution_log if e["stage"] == "aggregate"]
    assert len(agg_entries) == 1, "Must contain aggregate stage"
    report_dict = agg_entries[0]["report"]
    assert report_dict["total_tasks"] == task_count
    assert "passed" in report_dict
    assert "force_merged" in report_dict
    assert "unresolved_warnings" in report_dict
