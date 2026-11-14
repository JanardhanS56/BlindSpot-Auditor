import pytest
from orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_full_pipeline_rag_grounded_review():
    """Verify that full pipeline runs with RAG and Reviewer cites knowledge base standards."""
    orchestrator = Orchestrator()

    prompt = (
        "Write a Python utility module for calculating statistical metrics (mean, median) "
        "including type hints, error handling for empty lists, and docstrings conforming to style."
    )

    response = await orchestrator.run(prompt)
    assert response, "Final merged response must not be empty"

    # Inspect the execution log for audit stages
    audit_entries = [e for e in orchestrator.execution_log if e["stage"] == "audit"]
    assert len(audit_entries) > 0, "At least one task must be audited"

    # Verify that references in verdict cite actual knowledge base files
    found_kb_citation = False
    valid_kb_files = [
        "python-style-guide.md",
        "code-review-checklist.md",
        "api-design-standards.md",
        "general-requirements.md",
    ]

    for entry in audit_entries:
        refs = entry.get("references", [])
        assert isinstance(refs, list)
        for ref in refs:
            if any(kb_file in ref for kb_file in valid_kb_files):
                found_kb_citation = True
                break

    assert found_kb_citation, (
        f"Expected at least one verdict to cite a knowledge_base file. Entries: {audit_entries}"
    )
