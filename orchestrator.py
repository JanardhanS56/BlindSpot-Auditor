import asyncio
import logging
from typing import Any
from agents.implementer import ImplementerAgent
from agents.leader import LeaderAgent
from agents.reviewer import ReviewerAgent
from config import MAX_RETRIES
from models import AggregateReport, Issue, Task, TaskResult, Verdict
from rag.embedder import NvidiaEmbedder
from rag.indexer import KnowledgeBaseIndexer
from rag.retriever import KnowledgeRetriever
from rag.setup_db import get_connection, setup_database

logger = logging.getLogger(__name__)


class Orchestrator:
    """Manages the multi-agent event loop: decompose -> implement -> review -> merge."""

    def __init__(
        self,
        leader: LeaderAgent | None = None,
        implementer: ImplementerAgent | None = None,
        reviewer: ReviewerAgent | None = None,
        embedder: NvidiaEmbedder | None = None,
        retriever: KnowledgeRetriever | None = None,
        max_retries: int = MAX_RETRIES,
    ):
        self.embedder = embedder or NvidiaEmbedder()
        self.retriever = retriever or KnowledgeRetriever(embedder=self.embedder)
        self.leader = leader or LeaderAgent()
        self.implementer = implementer or ImplementerAgent()
        self.reviewer = reviewer or ReviewerAgent(retriever=self.retriever)
        self.max_retries = max_retries
        self.logger = logging.getLogger("orchestrator")
        self.execution_log: list[dict[str, Any]] = []

    async def ensure_indexed(self) -> int:
        """Ensures the knowledge base is indexed in pgvector on startup."""
        setup_database()
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM document_embeddings;")
            count = cur.fetchone()[0]
            cur.close()
            conn.close()

            if count == 0:
                self.logger.info("document_embeddings table is empty. Ingesting knowledge base...")
                indexer = KnowledgeBaseIndexer(embedder=self.embedder)
                indexed_count = await indexer.index_all()
                return indexed_count
            return count
        except Exception as e:
            self.logger.warning("Could not check or run initial indexing: %s", e)
            return 0

    async def _process_task(self, task: Task) -> tuple[TaskResult, Verdict]:
        """Encapsulates generate -> review -> retry loop for a single task."""
        self.logger.info("Starting workflow for task %s: %s", task.id, task.description[:60])
        resolved = False
        last_result: TaskResult | None = None
        last_verdict: Verdict | None = None

        while not resolved:
            try:
                # Implementer generates output
                prev_text = last_result.content if last_result else None
                result: TaskResult = await self.implementer.generate(task, previous_content=prev_text)
                last_result = result
            except Exception as gen_err:
                self.logger.error("Implementer error for task %s: %s", task.id, gen_err)
                last_result = TaskResult(
                    task_id=task.id,
                    content=f"Error generating implementation: {gen_err}",
                    metadata={"error": str(gen_err), "attempt": task.attempt},
                )

            try:
                # Reviewer audits output (grounded in RAG)
                verdict: Verdict = await self.reviewer.audit(task, last_result)
                last_verdict = verdict
            except Exception as rev_err:
                self.logger.error("Reviewer error for task %s: %s", task.id, rev_err)
                last_verdict = Verdict(
                    task_id=task.id,
                    passed=False,
                    issues=[Issue(severity="critical", description=f"Reviewer exception: {rev_err}")],
                    references=["Fallback audit"],
                    confidence=0.0,
                    summary=f"FAIL - Reviewer exception: {rev_err}",
                )

            self.execution_log.append({
                "stage": "audit",
                "task_id": task.id,
                "attempt": task.attempt,
                "passed": last_verdict.passed,
                "summary": last_verdict.summary,
                "references": last_verdict.references,
                "issues": [i.model_dump() for i in last_verdict.issues],
            })

            if last_verdict.passed:
                self.logger.info("Task %s PASSED on attempt %d", task.id, task.attempt)
                resolved = True
            else:
                self.logger.warning(
                    "Task %s FAILED on attempt %d: %s",
                    task.id,
                    task.attempt,
                    last_verdict.summary,
                )

                if task.attempt >= self.max_retries:
                    self.logger.warning(
                        "Task %s force-merged after %d failed attempts. Unresolved issue: %s",
                        task.id,
                        task.attempt,
                        last_verdict.summary,
                    )
                    resolved = True
                else:
                    # Re-dispatch with reviewer notes including cited sources
                    notes_list = [f"Verdict: {last_verdict.summary}"]
                    if last_verdict.references:
                        notes_list.append(
                            "Governing Standards & References:\n"
                            + "\n".join(f"- {ref}" for ref in last_verdict.references)
                        )

                    notes_list.append("Specific Issues to Address:")
                    primary_ref = (
                        last_verdict.references[0]
                        if last_verdict.references
                        else "project standards"
                    )
                    for issue in last_verdict.issues:
                        loc = f" at {issue.location}" if issue.location else ""
                        sug = f" Suggestion: {issue.suggestion}" if issue.suggestion else ""
                        notes_list.append(
                            f"- [{issue.severity.upper()}]{loc}: {issue.description} (per {primary_ref}).{sug}"
                        )

                    task.attempt += 1
                    task.reviewer_notes = "\n".join(notes_list)
                    self.logger.info(
                        "Re-dispatching task %s for attempt %d with cited reviewer notes",
                        task.id,
                        task.attempt,
                    )

        if last_result is None:
            last_result = TaskResult(task_id=task.id, content="")
        if last_verdict is None:
            last_verdict = Verdict(task_id=task.id, passed=True, summary="Default pass")

        return last_result, last_verdict

    def aggregate_verdicts(
        self,
        results: list[tuple[TaskResult, Verdict]],
    ) -> AggregateReport:
        """Aggregates all task verdicts into a comprehensive quality report."""
        total_tasks = len(results)
        passed = 0
        failed_then_passed = 0
        force_merged = 0
        unresolved_warnings: list[str] = []

        total_issues_found = sum(
            len(entry.get("issues", []))
            for entry in self.execution_log
            if entry.get("stage") == "audit"
        )

        for result, verdict in results:
            attempt = result.metadata.get("attempt", 1)
            if verdict.passed:
                if attempt > 1:
                    failed_then_passed += 1
                else:
                    passed += 1
            else:
                force_merged += 1
                warning_msg = (
                    f"Task {result.task_id} force-merged after {attempt} failed attempts. "
                    f"Unresolved issue: {verdict.summary}"
                )
                unresolved_warnings.append(warning_msg)

        unresolved_issues_count = sum(
            len(verdict.issues) for _, verdict in results if not verdict.passed
        )
        issues_resolved = max(0, total_issues_found - unresolved_issues_count)

        return AggregateReport(
            total_tasks=total_tasks,
            passed=passed,
            failed_then_passed=failed_then_passed,
            force_merged=force_merged,
            total_issues_found=total_issues_found,
            issues_resolved=issues_resolved,
            unresolved_warnings=unresolved_warnings,
        )

    async def run(self, prompt: str) -> str:
        """Executes the complete AKILI-SPECS workflow for a user prompt."""
        self.logger.info("Starting orchestration for prompt: %s", prompt[:80])
        self.execution_log.clear()

        # Ensure RAG knowledge base is available
        await self.ensure_indexed()

        # Step 1: Leader decomposes the prompt
        tasks: list[Task] = await self.leader.decompose(prompt)
        self.execution_log.append({
            "stage": "decompose",
            "task_count": len(tasks),
            "task_ids": [t.id for t in tasks],
        })

        # Step 2: Process tasks concurrently in parallel
        task_outcomes: list[tuple[TaskResult, Verdict]] = await asyncio.gather(
            *[self._process_task(task) for task in tasks]
        )

        passed_results: list[TaskResult] = [res for res, _ in task_outcomes]
        report: AggregateReport = self.aggregate_verdicts(task_outcomes)

        self.execution_log.append({
            "stage": "aggregate",
            "report": report.model_dump(),
        })

        # Step 3: Leader merges all outputs
        self.logger.info(
            "Merging %d results (passed: %d, retried_passed: %d, force_merged: %d)",
            len(passed_results),
            report.passed,
            report.failed_then_passed,
            report.force_merged,
        )
        final_answer: str = await self.leader.merge(
            passed_results,
            warnings=report.unresolved_warnings,
        )
        self.execution_log.append({
            "stage": "merge",
            "warnings_count": len(report.unresolved_warnings),
        })

        return final_answer
