# AKILI-SPECS: BlindSpot Auditor

> **Autonomous Knowledge-Integrated Leader-Implementer Multi-Agent Code Quality System**  
> A multi-agent MCP server with separate execution and audit roles, grounded by pgvector-based retrieval-augmented generation (RAG).

---

## 1. System Overview

Single-agent LLM systems can suffer from confirmation bias: a model that writes code and then reviews its own work may overlook edge cases or approve its own omissions. AKILI-SPECS addresses this by separating planning, implementation, and review:

- **Leader Agent**: Decomposes prompts into independent tasks, plans execution, and merges finalized outputs. It has no code-writing tools.
- **Implementer Agent**: Generates code for assigned tasks and can execute independent work concurrently via `asyncio.gather`.
- **Reviewer Agent**: Performs read-only audits of changes against standards retrieved from the RAG knowledge base. It cannot edit code.

```text
                           ┌─────────────────────────────────────────┐
                           │          MCP Server (handle_prompt)     │
                           └────────────────────┬────────────────────┘
                                                │
                                                ▼
                           ┌─────────────────────────────────────────┐
                           │         Orchestrator Event Loop         │
                           └────────┬──────────────────────┬─────────┘
                                    │                      │
                                    ▼                      │
                           ┌──────────────────┐            │
                           │   Leader Agent   │            │
                           │ (Decomposition)  │            │
                           └────────┬─────────┘            │
                                    │ Sub-tasks             │
                                    ▼                       │
                     ┌──────────────────────────────┐      │
                     │ Parallel Implementers        │      │
                     │ (asyncio.gather)             │      │
                     │ Task 1   | Task 2   | Task 3 │      │
                     └──────────────┬───────────────┘      │
                                    │ Outputs               │
                                    ▼                       ▼
                     ┌──────────────────────────────┐  ┌──────────────────┐
                     │ Reviewer Agent (Read-Only)   │◄─┤ RAG Knowledge    │
                     │ - Audits diffs vs standards  │  │ Base (pgvector + │
                     │ - Cites relevant guidelines │  │ Nemotron Embed)  │
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

- **Concurrent task dispatch**: Independent sub-tasks run in parallel using `asyncio.gather`, reducing end-to-end wall-clock latency while maintaining isolated task context.
- **RAG-grounded auditing**: Code reviews query a pgvector database indexed with coding standards, API specifications, and review checklists, using NVIDIA Nemotron-3.5-Embed-8B embeddings.
- **Verdict citations**: Reviews cite governing documents (for example, `python-style-guide.md` and `api-design-standards.md`) and identify line-level issues.
- **Structured feedback loop**: Failed implementations receive targeted feedback and can retry up to `MAX_RETRIES` (default: 3). If an issue remains unresolved, the system can force-merge with an explicit caveat.
- **MCP server safeguards**: Includes a 120-second execution timeout with partial results on overrun, automatic Groq rate-limit retries, and pgvector fallback behavior.

---

## 3. Architecture & Components

| Component | File | Responsibilities |
| :--- | :--- | :--- |
| **MCP Server** | [`mcp_server.py`](mcp_server.py) | FastMCP server exposing `handle_prompt`, with judge-facing metadata and timeout controls. |
| **Orchestrator** | [`orchestrator.py`](orchestrator.py) | Coordinates the pipeline event loop, task queues, concurrency, retry budget, and aggregation. |
| **Leader Agent** | [`agents/leader.py`](agents/leader.py) | Decomposes prompts into independent sub-tasks and synthesizes final multi-part deliverables. |
| **Implementer Agent** | [`agents/implementer.py`](agents/implementer.py) | Generates code for assigned tasks and incorporates prior diffs and reviewer feedback. |
| **Reviewer Agent** | [`agents/reviewer.py`](agents/reviewer.py) | Audits changes against retrieved RAG standards and emits structured findings. |
| **RAG Embedder** | [`rag/embedder.py`](rag/embedder.py) | Creates NVIDIA Nemotron embeddings with normalization and configured query prefixes. |
| **RAG Retriever** | [`rag/retriever.py`](rag/retriever.py) | Queries pgvector using cosine similarity, threshold filtering, and fallback retrieval. |

---

## 4. Setup, Database & Quickstart

The database schema is created automatically on startup. The standards corpus is embedded and inserted by the indexing script. PostgreSQL can be run locally or launched as a pgvector container with Docker.

### Step 1: Clone and install dependencies

Replace `<OWNER>` with the GitHub account or organization that hosts this repository.

```bash
git clone https://github.com/<OWNER>/BlindSpot-Auditor.git
cd BlindSpot-Auditor
pip install -r requirements.txt
```

### Step 2: Start the database

**Option A: Docker (recommended)**

```bash
docker run -d --name blindspot-db -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=postgres \
  ankane/pgvector
```

**Option B: Existing PostgreSQL installation**

Ensure PostgreSQL is running on port `5432` and that the database credentials match your `.env` configuration. The database must support the `pgvector` extension for vector-based retrieval.

### Step 3: Configure API keys and environment variables

Copy the template and edit `.env` with your API keys and database settings:

```bash
cp .env.example .env
```

- **Groq API key**: Available from [Groq Console](https://console.groq.com/keys).
- **NVIDIA API key**: Available from [NVIDIA Build](https://build.nvidia.com/nvidia/nemotron-3_5-embed-8b-bf16).
- **Database credentials**: The defaults below are suitable for the Docker command above; change them if your database uses different settings.

```env
GROQ_API_KEY=gsk_your_groq_key_here
NVIDIA_API_KEY=nvapi_your_nvidia_key_here
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_MAINTAINANCE_DB=postgres
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=postgres
```

### Step 4: Index the knowledge base

Run the indexing pipeline to create the database table, read the standard documents in `knowledge_base/`, generate 4,096-dimensional embeddings, and store them in PostgreSQL:

```bash
python -m rag.indexer
```

Expected output resembles:

```text
Successfully indexed 17 chunks across 4 documents into document_embeddings table.
```

### Step 5: Run the system

**Quick command-line prompt**

```bash
python -c "import asyncio; from orchestrator import Orchestrator; asyncio.run(Orchestrator().run('Write a thread-safe singleton in Python with type hints and docstrings'))"
```

**Integration test**

```bash
python -m pytest tests/test_integration_final.py -v -s
```

**Benchmark evaluation**

```bash
python tests/run_evaluation.py
```

---

## 5. Connecting to Claude Desktop / Cursor (MCP Mode)

Start the MCP server using stdio transport:

```bash
python mcp_server.py --transport stdio
```

Add a server entry to `claude_desktop_config.json` or your IDE's MCP configuration. Replace `/path/to/BlindSpot-Auditor` with the absolute path to the repository on your system:

```json
{
  "mcpServers": {
    "blindspot-auditor": {
      "command": "python",
      "args": ["-u", "/path/to/BlindSpot-Auditor/mcp_server.py", "--transport", "stdio"],
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

The evaluation compares a single-agent baseline with the multi-agent system across five prompt categories designed to exercise concurrency, reasoning, and retrieval behavior.

Run the full evaluation suite:

```bash
python tests/run_evaluation.py
```

### Quantitative benchmark results

| Prompt ID | Category & Trap | Baseline (s) | Triad (s) | Tasks | Retries | Force Merges | RAG Citations | Outcome |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| `code-gen` | LRU Cache with TTL (race condition & lock granularity) | 8.2 | 87.5 | 3 | 0 | 0 | 3 | **Triad caught race conditions**; partitioned cache into lock-safe methods. |
| `research` | Microservices vs. Monolith trade-offs for a 5-dev team | 4.5 | 40.9 | 1 | 1 | 0 | 2 | **Triad audited formatting** and enforced actionable small-team sizing. |
| `logic` | High-throughput distributed rate-limiter logic | 8.6 | 142.0 | 3 | 2 | 0 | 5 | **Triad detected clock skew & memory leaks**, prompting two corrective revisions. |
| `mixed` | Social media database schema (indexes & FK constraints) | 12.0 | 90.8 | 2 | 0 | 0 | 1 | **Triad verified composite indexes** on follower lookups. |
| `hallucination` | Fabricated "Robertson-Walker consensus theorem" | 10.6 | 213.4 | 2 | 1 | 1 | 7 | **RAG returned no matches**; the reviewer flagged the theorem as unsupported and the leader merged with a caveat. |

Detailed side-by-side evaluation artifacts are available in [`tests/eval_results/`](tests/eval_results/).

---

## 7. Testing Suite

The project includes unit, smoke, RAG, and integration tests:

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

```text
.
├── config.py                     # Configuration and environment settings
├── models.py                     # Pydantic schemas (Task, Verdict, AggregateReport)
├── llm_client.py                 # Groq LLM client with fallback and rate-limit resilience
├── orchestrator.py               # Core multi-agent loop with asyncio.gather
├── mcp_server.py                 # FastMCP server entry point
├── requirements.txt              # Project dependencies
├── model_card.md                 # NVIDIA Nemotron-3.5 embedding model specification
├── knowledge_base/               # Standard documents for RAG grounding
│   ├── README.md
│   ├── python-style-guide.md
│   ├── code-review-checklist.md
│   ├── api-design-standards.md
│   └── general-requirements.md
├── agents/                       # Agent implementations
│   ├── base.py                   # Abstract base agent
│   ├── leader.py                 # Planning, decomposition, and merging
│   ├── implementer.py            # Stateless code generation
│   └── reviewer.py               # Read-only audit with RAG context
├── rag/                          # RAG vector storage and retrieval
│   ├── chunker.py                # Markdown header and token-aware chunker
│   ├── embedder.py               # NVIDIA Nemotron embedding client
│   ├── indexer.py                # Corpus loader and vector store populator
│   ├── retriever.py              # Vector similarity search engine
│   └── setup_db.py               # PostgreSQL / pgvector database setup
└── tests/                        # Evaluation and test suites
    ├── test_baseline.py          # SingleAgentBaseline implementation
    ├── run_evaluation.py         # Evaluation runner comparing baseline vs triad
    ├── test_smoke.py             # Agent and loop smoke tests
    ├── test_rag.py               # Embedder and retriever unit tests
    ├── test_integration_final.py # End-to-end integration test
    └── eval_results/             # Benchmark outputs
```

---

## 9. License

MIT License. See [`LICENSE`](LICENSE) for details.
