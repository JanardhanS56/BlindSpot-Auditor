import logging
from typing import Any
from agents.implementer import ImplementerAgent
from agents.leader import LeaderAgent
from agents.reviewer import ReviewerAgent
from config import MAX_RETRIES
from models import Task, TaskResult, Verdict
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

        passed_results: list[TaskResult] = []
        warnings: list[str] = []

        # Step 2: Process tasks
        for task in tasks:
            self.logger.info("Starting workflow for task %s: %s", task.id, task.description[:60])
            resolved = False

            while not resolved:
                # Implementer generates output
                result: TaskResult = await self.implementer.generate(task)

                # Reviewer audits output (grounded in RAG)
                verdict: Verdict = await self.reviewer.audit(task, result)

                self.execution_log.append({
                    "stage": "audit",
                    "task_id": task.id,
                    "attempt": task.attempt,
                    "passed": verdict.passed,
                    "summary": verdict.summary,
                    "references": verdict.references,
                })

                if verdict.passed:
                    self.logger.info("Task %s PASSED on attempt %d", task.id, task.attempt)
                    passed_results.append(result)
                    resolved = True
                else:
                    self.logger.warning(
                        "Task %s FAILED on attempt %d: %s",
                        task.id,
                        task.attempt,
                        verdict.summary,
                    )

                    if task.attempt >= self.max_retries:
                        warning_msg = (
                            f"Task {task.id} force-merged after {task.attempt} failed attempts. "
                            f"Unresolved issue: {verdict.summary}"
                        )
                        self.logger.warning(warning_msg)
                        warnings.append(warning_msg)
                        passed_results.append(result)
                        resolved = True
                    else:
                        # Re-dispatch with reviewer notes
                        notes_list = [f"Verdict: {verdict.summary}"]
                        for issue in verdict.issues:
                            loc = f" at {issue.location}" if issue.location else ""
                            sug = f" Suggestion: {issue.suggestion}" if issue.suggestion else ""
                            notes_list.append(f"- [{issue.severity.upper()}]{loc}: {issue.description}.{sug}")

                        task.attempt += 1
                        task.reviewer_notes = "\n".join(notes_list)
                        self.logger.info(
                            "Re-dispatching task %s for attempt %d with reviewer notes",
                            task.id,
                            task.attempt,
                        )

        # Step 3: Leader merges all outputs
        self.logger.info("Merging %d results with %d warnings", len(passed_results), len(warnings))
        final_answer: str = await self.leader.merge(passed_results, warnings=warnings)
        self.execution_log.append({
            "stage": "merge",
            "warnings_count": len(warnings),
        })

        return final_answer
