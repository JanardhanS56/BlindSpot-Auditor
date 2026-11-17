# AKILI-SPECS: BlindSpot Auditor

> **Autonomous Knowledge-Integrated Leader-Implementer Multi-Agent Code Quality System**  
> *A multi-agent MCP server featuring architectural separation of execution and audit, grounded by pgvector RAG.*

---

## 1. System Overview & Core Thesis

Single-agent LLM systems suffer from an inherent **confirmation bias**: when the same model writes code and is then prompted to "review" it, it routinely approves its own edge-case omissions, hallucinations, and structural bugs.

**AKILI-SPECS** solves this through **strict architectural separation**:
- **Leader Agent**: Decomposes user prompts into independent sub-tasks, plans execution, and merges finalized outputs. Zero write tools.
- **Implementer Agent**: Stateless code generator executing sub-tasks concurrently in parallel via `asyncio.gather`.
- **Reviewer Agent**: **Architecturally read-only** audit agent. It cannot edit code—it can only judge diffs against standards retrieved from a RAG knowledge base. Zero incentive to approve flaws.

```
                           ┌─────────────────────────────────────────┐
                           │          MCP Server (handle_prompt)     │
                           └────────────────────┬────────────────────┘
                                                │
                                                ▼
                           ┌─────────────────────────────────────────┐
                           │         Orchestrator Event Loop         │
                           └────────┬───────────────────────┬────────┘
                                    │                       │
                                    ▼                       │
                           ┌──────────────────┐             │
                           │   Leader Agent   │             │
                           │ (Decomposition)  │             │
                           └────────┬─────────┘             │
                                    │ Sub-tasks             │
                                    ▼                       │
                     ┌──────────────────────────────┐       │
                     │ Parallel Implementers        │       │
                     │ (asyncio.gather)             │       │
                     │ Task 1   | Task 2   | Task 3 │       │
                     └──────────────┬───────────────┘       │
                                    │ Outputs               │
                                    ▼                       ▼
                     ┌──────────────────────────────┐  ┌──────────────────┐
                     │ Reviewer Agent (Read-Only)   │◄─┤ RAG Knowledge    │
                     │ - Audits diffs vs standards  │  │ Base (pgvector + │
                     │ - Cites external guidelines  │  │ Nemotron Embed)  │
                     └──────────────┬───────────────┘  └──────────────────┘
                                    │ PASS / FAIL (with retry loop)
                                    ▼
                           ┌──────────────────┐
                           │   Leader Agent   │
                           │  (Merge & Caveat)│
                           └────────┬─────────┘
                                    │
                                    ▼
                           Final Judge-Ready Output
```

---

## 2. Key Features

- **Concurrent Task Dispatch**: Independent sub-tasks run in parallel using `asyncio.gather`, minimizing end-to-end wall-clock latency while maintaining isolated task context.
- **RAG-Grounded Auditing**: Every code review queries a pgvector database indexed with coding standards, API specs, and review checklists using NVIDIA Nemotron-3.5-Embed-8B embeddings.
- **Guaranteed Verdict Citations**: Reviews explicitly cite governing documents (e.g., `python-style-guide.md`, `api-design-standards.md`) and pinpoint line-level issues.
- **Structured Feedback Loop**: Failed implementations receive targeted feedback and retry up to `MAX_RETRIES` (default: 3). If unresolvable, the system gracefully force-merges with explicit `## ⚠ Unresolved Concerns` caveats.
- **Production-Hardened MCP Server**: Built-in 120s execution timeout returning partial results on overrun, automatic Groq rate-limit retries, and pgvector fallback.

---

## 3. Architecture & Components

| Component | File | Responsibilities | Tools Allowed |
| :--- | :--- | :--- | :--- |
| **MCP Server** | [mcp_server.py](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/mcp_server.py) | FastMCP server exposing `handle_prompt` with judge-facing metadata and timeout controls. | Stdio / SSE / HTTP |
| **Orchestrator** | [orchestrator.py](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/orchestrator.py) | Coordinates pipeline event loop, task queues, concurrency, retry budget, and aggregate verdict reporting. | Internal Agents |
| **Leader Agent** | [agents/leader.py](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/agents/leader.py) | Analyzes prompts into independent sub-tasks; synthesizes final multi-part deliverables with warning sections. | None (Planning only) |
| **Implementer Agent** | [agents/implementer.py](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/agents/implementer.py) | Stateless code generation; incorporates previous diffs and reviewer feedback on revision cycles. | Code Generation |
| **Reviewer Agent** | [agents/reviewer.py](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/agents/reviewer.py) | Performs strict line-by-line audits against retrieved RAG standards; emits structured `Verdict` objects. | Read-Only Audit |
| **RAG Embedder** | [rag/embedder.py](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/rag/embedder.py) | NVIDIA Nemotron-3.5 4096-dim embeddings with L2 normalization, query prefixes, and local response caching. | REST (NVIDIA API) |
| **RAG Retriever** | [rag/retriever.py](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/rag/retriever.py) | Cosine similarity query engine against pgvector with threshold filtering and array fallback. | PostgreSQL |

---

## 4. Setup & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- PostgreSQL with `pgvector` extension (optional; system includes automatic array-fallback for environments without native pgvector)
- Groq API Key
- NVIDIA API Key

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/janardhan-dev/BlindSpot-Auditor.git
cd BlindSpot-Auditor
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the project root:
```env
# LLM Provider (Groq)
GROQ_API_KEY=your_groq_api_key_here
DEFAULT_MODEL=openai/gpt-oss-120b

# NVIDIA Embeddings API
NVIDIA_API_KEY=your_nvidia_api_key_here

# PostgreSQL / pgvector
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_MAINTAINANCE_DB=postgres
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=your_postgres_password

# Pipeline & RAG Optimization
MAX_RETRIES=3
PIPELINE_TIMEOUT=120.0
RAG_TOP_K=5
RAG_MIN_SIMILARITY=0.3
EMBEDDING_DIM=4096
EMBEDDING_TRUNCATE=false
```

### 3. Initialize & Index Knowledge Base
Populate the vector store with the coding standards corpus:
```bash
python -m rag.indexer
```

---

## 5. Usage

### Running as an MCP Server
To expose the system to MCP clients (such as Claude Desktop, Antigravity, or Cursor):
```bash
# Stdio transport (default)
python mcp_server.py --transport stdio

# SSE transport
python mcp_server.py --transport sse
```

#### MCP Client Configuration
Add the server to your `claude_desktop_config.json` or `mcp_settings.json`:
```json
{
  "mcpServers": {
    "blindspot-auditor": {
      "command": "python",
      "args": ["-u", "c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/mcp_server.py", "--transport", "stdio"],
      "env": {
        "GROQ_API_KEY": "your_groq_api_key",
        "NVIDIA_API_KEY": "your_nvidia_api_key"
      }
    }
  }
}
```

---

## 6. Evaluation: Single-Agent Baseline vs. AKILI-SPECS Triad

To rigorously prove the thesis—**"Does the multi-agent team beat a single agent working alone?"**—we evaluated 5 challenging prompt categories containing deliberate traps (subtle concurrency bugs, missing SQL indexes, edge-case logic, and hallucination probes).

Run the full evaluation suite:
```bash
python tests/run_evaluation.py
```

### Quantitative Benchmark Results

| Prompt ID | Category & Trap | Baseline (s) | Triad (s) | Tasks | Retries | Force Merges | RAG Citations | Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `code-gen` | LRU Cache with TTL (race condition & lock granularity) | 8.2s | 87.5s | 3 | 0 | 0 | 3 | **Triad caught race conditions**; partitioned cache into lock-safe methods. |
| `research` | Microservices vs. Monolith trade-offs for 5-dev team | 4.5s | 40.9s | 1 | 1 | 0 | 2 | **Triad audited formatting** and enforced actionable small-team sizing. |
| `logic` | High-throughput distributed rate-limiter logic | 8.6s | 142.0s | 3 | 2 | 0 | 5 | **Triad detected clock skew & memory leaks**, forcing 2 corrective revisions. |
| `mixed` | Social media database schema (indexes & FK constraints) | 12.0s | 90.8s | 2 | 0 | 0 | 1 | **Triad verified composite indexes** on follower lookups. |
| `hallucination`| Fabricated "Robertson-Walker consensus theorem" | 10.6s | 213.4s | 2 | 1 | 1 | 7 | **Triad RAG returned 0 matches**; Reviewer flagged theorem as unsupported; Leader merged with warning caveat. |

Detailed side-by-side markdown artifacts for all prompts are stored in [tests/eval_results/](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/tests/eval_results).

---

## 7. Testing Suite

The project includes unit, smoke, RAG, and comprehensive integration tests:
```bash
# Run smoke tests
python -m pytest tests/test_smoke.py

# Run RAG vector search tests
python -m pytest tests/test_rag.py

# Run full parallel dispatch and RAG integration test
python -m pytest tests/test_integration_final.py
```

---

## 8. Repository Structure

```
.
├── config.py                 # Configuration and environment settings
├── models.py                 # Pydantic schemas (Task, Verdict, AggregateReport)
├── llm_client.py             # Groq LLM client with fallback & rate-limit resilience
├── orchestrator.py           # Core multi-agent loop with asyncio.gather
├── mcp_server.py             # FastMCP server entry point
├── requirements.txt          # Project dependencies
├── model_card.md             # NVIDIA Nemotron-3.5 embedding model specification
├── knowledge_base/           # Standard documents for RAG grounding
│   ├── python-style-guide.md
│   ├── code-review-checklist.md
│   ├── api-design-standards.md
│   └── general-requirements.md
├── agents/                   # Agent implementations
│   ├── base.py               # Abstract base agent
│   ├── leader.py             # Planning, decomposition, and merging
│   ├── implementer.py        # Stateless code generation
│   └── reviewer.py           # Read-only audit with RAG context
├── rag/                      # RAG vector storage and retrieval
│   ├── chunker.py            # Markdown header and token-aware chunker
│   ├── embedder.py           # NVIDIA Nemotron embedding client
│   ├── indexer.py            # Corpus loader and vector store populator
│   ├── retriever.py          # Vector similarity search engine
│   └── setup_db.py           # PostgreSQL / pgvector database setup
└── tests/                    # Evaluation and test suites
    ├── test_baseline.py      # SingleAgentBaseline implementation
    ├── run_evaluation.py     # Evaluation runner comparing baseline vs triad
    ├── test_smoke.py         # Agent and loop smoke tests
    ├── test_rag.py           # Embedder and retriever unit tests
    ├── test_integration_final.py # End-to-end integration test
    └── eval_results/         # 10 side-by-side benchmark outputs
```

---

## 9. License

MIT License. See LICENSE for details.
