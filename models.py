from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4
from pydantic import BaseModel, Field


class Task(BaseModel):
    id: str = Field(default_factory=lambda: f"task-{uuid4().hex[:8]}")
    description: str
    requirements: list[str] = Field(default_factory=list)
    context: str | None = None
    priority: int = 1
    attempt: int = 1
    reviewer_notes: str | None = None


class TaskResult(BaseModel):
    task_id: str
    content: str
    diff: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Issue(BaseModel):
    severity: Literal["critical", "major", "minor", "style"]
    description: str
    location: str | None = None
    suggestion: str | None = None


class Verdict(BaseModel):
    task_id: str
    passed: bool
    issues: list[Issue] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    summary: str


class AgentMessage(BaseModel):
    sender: Literal["leader", "implementer", "reviewer", "orchestrator"]
    recipient: Literal["leader", "implementer", "reviewer", "orchestrator"]
    payload: Task | TaskResult | Verdict | str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
