# AKILI-SPECS System Design

## 1. System Identity

**AKILI-SPECS** — Autonomous Knowledge-Integrated Leader-Implementer (Separated Procedures for Ensured Code Standards)

A multi-agent MCP server where a **Leader** orchestrates, **Implementers** write, and a **Reviewer** audits — with zero overlap in responsibilities.

---

## 2. Core Thesis

> A Reviewer that **cannot edit** code has zero incentive to approve it. This is an architectural constraint, not a prompt trick.

The confirmation bias problem in single-agent systems is not solvable by telling the same agent to "review carefully." It requires **structural separation**: different agents, different tools, different context windows.

---

## 3. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    MCP SERVER (Entry Point)                   │
│  Accepts prompt from judge's assistant → returns final answer │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Event Loop)                   │
│  Manages async task queue, dispatch, feedback routing          │
└─────────┬──────────────────────────────┬─────────────────────┘
          │                              │
          ▼                              │
┌─────────────────────┐                  │
│   🧠 LEADER AGENT    │                  │
│                     │                  │
│ - Decomposes prompt │                  │
│   into sub-tasks    │                  │
│ - Assigns to        │                  │
│   Implementers      │                  │
│ - Merges final      │                  │
│   answer            │                  │
│ - Handles FAIL      │                  │
│   re-dispatch       │                  │
│                     │                  │
│ Tools: NONE         │                  │
│ (planning only)     │                  │
└────────┬────────────┘                  │
         │ sub-tasks                     │
         ▼                               │
┌─────────────────────┐                  │
│ ⚙️ IMPLEMENTER(s)    │                  │
│                     │                  │
│ - Generates code /  │                  │
│   content per task  │                  │
│ - Returns output +  │                  │
│   diff              │                  │
│                     │                  │
│ Tools: WRITE        │                  │
│ (code generation,   │                  │
│  file creation)     │                  │
└────────┬────────────┘                  │
         │ output + diff                 │
         ▼                               │
┌─────────────────────┐    ┌─────────────┴──────────┐
│ 🔍 REVIEWER AGENT    │◄──│   📚 RAG PIPELINE       │
│                     │    │                        │
│ - Audits diff       │    │ Query → Embed (NVIDIA) │
│   against standards │    │ → pgvector search      │
│ - Checks for:       │    │ → Top-K chunks         │
│   • Logic errors    │    │ → Inject into Reviewer  │
│   • Style violations│    │   context              │
│   • Hallucinations  │    └────────────────────────┘
│   • Contradictions  │
│   • Unsupported     │
│     claims          │
│                     │
│ Tools: READ-ONLY    │
│ (cannot modify code)│
│                     │
│ Output: Verdict     │
│ {pass, issues[],    │
│  references[]}      │
└────────┬────────────┘
         │ verdict
         ▼
   ┌─────────────┐
   │ PASS → Merge │──► Final Answer → MCP Response
   │ FAIL → Loop  │──► Re-dispatch with Reviewer notes (max 3 iterations)
   └─────────────┘
```

---

## 4. Component Contracts

### 4.1 Leader Agent

| Property | Value |
|---|---|
| **Input** | Raw user prompt (from MCP) |
| **Output** | `List[Task]` — structured sub-tasks |
| **Merge Input** | `List[TaskResult]` — all PASS'd outputs |
| **Merge Output** | `str` — final unified answer |
| **LLM** | Groq API |
| **Tools** | None — planning and merging only |
| **Context strategy** | Minimal — only sees prompt + task list + verdicts |

### 4.2 Implementer Agent

| Property | Value |
|---|---|
| **Input** | Single `Task` from Leader |
| **Output** | `TaskResult` with generated content/code + optional diff |
| **LLM** | Groq API |
| **Tools** | Write-capable (code generation, computation) |
| **Context strategy** | Full — sees the task, any prior FAIL notes, and sub-task context |

### 4.3 Reviewer Agent

| Property | Value |
|---|---|
| **Input** | `TaskResult` from Implementer + RAG-retrieved context |
| **Output** | `Verdict` — pass/fail + issues + references |
| **LLM** | Groq API |
| **Tools** | **Read-only** — can read files, query RAG, but cannot write |
| **Context strategy** | Focused — sees only the diff, the original task spec, and retrieved standards |

### 4.4 RAG Pipeline

| Property | Value |
|---|---|
| **Embedding Model** | NVIDIA Nemotron-3.5-Embed-8B (4096-dim, truncatable to 1024) |
| **Vector Store** | pgvector on local PostgreSQL |
| **Corpus** | Project style guides, requirements, coding standards, API specs |
| **Retrieval** | Cosine similarity, top-K (K=5 default) |
| **Integration** | Reviewer queries before every verdict |

---

## 5. Data Models (Pydantic)

```python
class Task(BaseModel):
    id: str                          # UUID
    description: str                 # What to do
    requirements: list[str]          # Acceptance criteria
    context: str | None              # Additional context from Leader
    priority: int = 1                # For ordering
    attempt: int = 1                 # Tracks re-dispatch count (max 3)
    reviewer_notes: str | None       # Injected on FAIL re-dispatch

class TaskResult(BaseModel):
    task_id: str                     # References Task.id
    content: str                     # Generated code/text
    diff: str | None                 # Optional diff representation
    metadata: dict                   # Token usage, timing, etc.

class Verdict(BaseModel):
    task_id: str                     # References Task.id
    passed: bool                     # PASS or FAIL
    issues: list[Issue]              # Specific problems found
    references: list[str]            # RAG sources that grounded the review
    confidence: float                # 0.0–1.0 reviewer confidence
    summary: str                     # One-line verdict summary

class Issue(BaseModel):
    severity: Literal["critical", "major", "minor", "style"]
    description: str                 # What's wrong
    location: str | None             # Where in the output
    suggestion: str | None           # How to fix it

class AgentMessage(BaseModel):
    sender: Literal["leader", "implementer", "reviewer", "orchestrator"]
    recipient: Literal["leader", "implementer", "reviewer", "orchestrator"]
    payload: Task | TaskResult | Verdict | str
    timestamp: datetime
```

---

## 6. Communication Flow

```
User Prompt
    │
    ▼
[MCP Server] ──► [Orchestrator]
                      │
                      ▼
                 [Leader.decompose(prompt)]
                      │
                      ▼
                 Task Queue: [T1, T2, T3, ...]
                      │
              ┌───────┼───────┐
              ▼       ▼       ▼        (parallel)
          [Impl-1] [Impl-2] [Impl-N]
              │       │       │
              ▼       ▼       ▼
          [Result1] [Result2] [ResultN]
              │       │       │
              └───────┼───────┘
                      ▼
                 Review Queue: [R1, R2, R3, ...]
                      │
                      ▼              (sequential — one Reviewer)
                 [Reviewer.audit(result, rag_context)]
                      │
                 ┌────┴────┐
                 ▼         ▼
              [PASS]    [FAIL]
                 │         │
                 ▼         ▼
           Collect    Re-dispatch to Implementer
                 │    (with reviewer_notes, attempt++)
                 │         │
                 │    if attempt > 3:
                 │         ▼
                 │    Force-merge with warnings
                 │         │
                 └────┬────┘
                      ▼
                 [Leader.merge(all_passed_results)]
                      │
                      ▼
                 Final Answer → MCP Response
```

---

## 7. Key Design Decisions

| Decision | Rationale |
|---|---|
| **Reviewer is read-only by architecture** | Eliminates confirmation bias structurally, not via prompting |
| **Leader never generates content** | Keeps Leader context window lean; prevents role bleed |
| **Max 3 retry attempts** | Prevents infinite FAIL loops; force-merge with warnings after 3 |
| **RAG before every review** | Reviewer judges against retrieved evidence, not parametric memory |
| **In-process async queues** | No external message broker needed; `asyncio.Queue` suffices for hackathon |
| **Groq for all LLM calls** | 500+ tok/s; free tier; open-source models (David vs Goliath angle) |
| **NVIDIA API for embeddings** | Nemotron-3.5-Embed-8B is production-grade; API avoids local GPU requirement |
| **pgvector over Chroma/FAISS** | User already has Postgres; pgvector is one `CREATE EXTENSION` away |
| **Cosine similarity, K=5** | Balanced recall vs. context injection cost |
| **4096-dim → 1024-dim truncation** | Available if latency is tight; L2-normalize after truncation |

---

## 8. Technology Stack

| Component | Technology | Version / Detail |
|---|---|---|
| Language | Python | 3.11+ |
| MCP Framework | `mcp` SDK | Latest |
| Web Framework | FastAPI (for MCP transport) | 0.100+ |
| LLM Provider | Groq API | LLaMA 3.3 70B / Mixtral 8x7B |
| Embedding Provider | NVIDIA API (`build.nvidia.com`) | Nemotron-3.5-Embed-8B |
| Vector Store | pgvector on PostgreSQL | Extension on existing Postgres |
| Async Runtime | `asyncio` | stdlib |
| Data Validation | Pydantic v2 | 2.0+ |
| HTTP Client | `httpx` | async-capable |
| Diff Engine | `difflib` | stdlib |
| Testing | `pytest` + `pytest-asyncio` | Latest |

---

## 9. File Structure (Final)

```
RAG Agent/
├── PLAN/                          # Planning documents (this folder)
├── agents/
│   ├── __init__.py
│   ├── base.py                    # BaseAgent ABC
│   ├── leader.py                  # LeaderAgent
│   ├── implementer.py             # ImplementerAgent
│   └── reviewer.py                # ReviewerAgent
├── rag/
│   ├── __init__.py
│   ├── embedder.py                # NVIDIA embedding client
│   ├── indexer.py                 # Corpus → pgvector ingestion
│   └── retriever.py               # Query → top-K retrieval
├── prompts/
│   ├── leader_system.md           # Leader system prompt
│   ├── implementer_system.md      # Implementer system prompt
│   └── reviewer_system.md         # Reviewer system prompt
├── knowledge_base/                # Documents to embed (style guides, specs)
│   └── README.md
├── tests/
│   ├── __init__.py
│   ├── test_agents.py
│   ├── test_rag.py
│   ├── test_orchestrator.py
│   ├── test_baseline.py           # Single-agent baseline comparison
│   └── eval_prompts.json          # Test prompts for evaluation
├── mcp_server.py                  # MCP entry point
├── orchestrator.py                # Async event loop
├── models.py                      # Pydantic data models
├── config.py                      # Settings, API keys, constants
├── requirements.txt
├── .env
├── .gitignore
├── model_card.md
└── akili-specs-plan.md
```
