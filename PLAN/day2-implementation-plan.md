# Day 2 Implementation Plan — RAG-Grounded Review

> **Prerequisite:** Day 1 complete (`v0.1.0` tagged). All agents work, pipeline runs end-to-end.
> **Goal:** The Reviewer now retrieves evidence from a vector DB before judging. Verdicts cite sources.

---

## Build Order (Each Step = 1 Micro-Commit)

### Step 1: pgvector Setup
**Commit:** `feat(rag): enable pgvector extension and create embeddings table`

Script: `rag/setup_db.py`
- Connect to local Postgres using `.env` credentials
- `CREATE EXTENSION IF NOT EXISTS vector;`
- Create table:
  ```sql
  CREATE TABLE IF NOT EXISTS document_embeddings (
      id SERIAL PRIMARY KEY,
      source_file TEXT NOT NULL,
      chunk_index INTEGER NOT NULL,
      content TEXT NOT NULL,
      embedding vector(4096),
      metadata JSONB DEFAULT '{}',
      created_at TIMESTAMP DEFAULT NOW()
  );
  CREATE INDEX ON document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
  ```
- Verify with a test insert + select

---

### Step 2: NVIDIA Embedding Client
**Commit:** `feat(rag): add NVIDIA Nemotron-3.5-Embed-8B embedding client`

File: `rag/embedder.py`
- Class `NvidiaEmbedder`:
  - Uses `httpx.AsyncClient` to call `https://integrate.api.nvidia.com/v1/embeddings`
  - Auth: `Authorization: Bearer {NVIDIA_API_KEY}`
  - Model: `nvidia/nemotron-3.5-embed-8b-bf16`
  - Input type parameter: `"passage"` for documents, `"query"` for queries
  - Returns: `list[float]` (4096-dim)
  - Method: `async def embed(self, text: str, input_type: str = "passage") -> list[float]`
  - Method: `async def embed_batch(self, texts: list[str], input_type: str = "passage") -> list[list[float]]`
  - Error handling: retry on 429 (rate limit)
  - Optional truncation to 1024-dim with L2 re-normalization

---

### Step 3: Text Chunker
**Commit:** `feat(rag): add text chunker for knowledge base documents`

File: `rag/chunker.py`
- Function: `def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]`
- Splits on paragraph boundaries (double newline) first, then sentence boundaries
- Each chunk is self-contained (includes enough context)
- Returns list of chunk strings
- Also: `def chunk_markdown(filepath: str) -> list[dict]`
  - Splits on `## ` headers
  - Returns `[{"content": str, "section": str, "source": str}]`

---

### Step 4: Knowledge Base Seed Documents
**Commit:** `docs(knowledge_base): add initial style guide and coding standards`

Files in `knowledge_base/`:
- `python-style-guide.md` — naming conventions, docstrings, type hints, error handling
- `code-review-checklist.md` — what a reviewer should check (edge cases, security, tests)
- `api-design-standards.md` — REST conventions, status codes, error formats
- `general-requirements.md` — all functions handle empty inputs, all code includes error handling

These are the documents the Reviewer will retrieve from. More can be added.

---

### Step 5: Indexer
**Commit:** `feat(rag): implement indexer — ingest knowledge_base/ into pgvector`

File: `rag/indexer.py`
- Class `KnowledgeBaseIndexer`:
  - Reads all `.md` files from `knowledge_base/`
  - Chunks each file using `chunker.py`
  - Embeds each chunk using `NvidiaEmbedder`
  - Inserts into `document_embeddings` table
  - Method: `async def index_all(self) -> int` (returns count of indexed chunks)
  - Method: `async def index_file(self, filepath: str) -> int`
  - Deduplication: skip if `source_file + chunk_index` already exists
- CLI entry point: `python -m rag.indexer` runs full indexing

---

### Step 6: Retriever
**Commit:** `feat(rag): implement retriever — query pgvector for relevant chunks`

File: `rag/retriever.py`
- Class `KnowledgeRetriever`:
  - Method: `async def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]`
    1. Embed query using `NvidiaEmbedder` (input_type="query")
    2. Query pgvector:
       ```sql
       SELECT content, source_file, chunk_index,
              1 - (embedding <=> %s::vector) AS similarity
       FROM document_embeddings
       ORDER BY embedding <=> %s::vector
       LIMIT %s;
       ```
    3. Filter by minimum similarity threshold (default 0.3)
    4. Return `RetrievedChunk` objects
- Model:
  ```python
  class RetrievedChunk(BaseModel):
      content: str
      source_file: str
      chunk_index: int
      similarity: float
  ```

---

### Step 7: Update Reviewer to Use RAG
**Commit:** `feat(reviewer): integrate RAG retrieval into audit() — verdicts now cite sources`

File: `agents/reviewer.py` (modify existing)
- Add `retriever: KnowledgeRetriever` to ReviewerAgent constructor
- Modify `audit()`:
  1. Extract review query from task description + result content
  2. `chunks = await self.retriever.retrieve(review_query)`
  3. Format chunks as context:
     ```
     RETRIEVED STANDARDS:
     [1] (from python-style-guide.md): "All functions must include type hints..."
     [2] (from code-review-checklist.md): "Check for empty input handling..."
     ```
  4. Inject into reviewer's user message before LLM call
  5. Verdict's `references` field now populated from actual retrieved sources

---

### Step 8: Update Reviewer System Prompt for RAG
**Commit:** `docs(prompts): update reviewer prompt — add RAG grounding instructions`

File: `prompts/reviewer_system.md` (modify existing)
- Add section:
  ```
  ## Grounding in Retrieved Standards
  You will receive RETRIEVED STANDARDS from the project's knowledge base.
  - ALWAYS check your review against these standards
  - CITE the specific standard when raising an issue (e.g., "per python-style-guide.md §3")
  - If no relevant standard is retrieved, note "No retrieved standard applicable"
    and review against general best practices
  - NEVER claim a standard exists that was not in the retrieved context
  ```

---

### Step 9: Update Orchestrator for RAG Init
**Commit:** `feat(orchestrator): initialize RAG components on startup`

File: `orchestrator.py` (modify existing)
- On init:
  1. Create `NvidiaEmbedder` instance
  2. Create `KnowledgeRetriever` instance
  3. Pass retriever to `ReviewerAgent`
- Add method: `async def ensure_indexed(self)` — runs indexer if DB is empty

---

### Step 10: Feedback Loop Enhancement
**Commit:** `feat(orchestrator): enhance feedback loop — reviewer notes include cited sources`

File: `orchestrator.py` (modify existing)
- When re-dispatching after FAIL:
  - Include the Reviewer's issue descriptions AND the referenced sources
  - Format: "The Reviewer found: {issue.description} (per {reference}). Address this."
  - This gives the Implementer the specific standard to comply with

---

### Step 11: RAG Unit Tests
**Commit:** `test(rag): add tests for embedder, indexer, and retriever`

File: `tests/test_rag.py`
- Test embedder returns 4096-dim vector
- Test indexer stores documents in pgvector
- Test retriever returns relevant chunks for a query
- Test retriever respects top_k and similarity threshold

---

### Step 12: Integration Test with RAG
**Commit:** `test: add integration test — reviewer cites retrieved standards in verdict`

File: `tests/test_rag_integration.py`
- Send a code generation prompt through full pipeline
- Assert Reviewer's verdict has non-empty `references`
- Assert references point to actual knowledge_base files

---

### Step 13: Day 2 Tag
```bash
git tag -a v0.2.0 -m "Day 2: RAG pipeline — NVIDIA embeddings, pgvector, grounded review"
```

---

## Day 2 Acceptance Checklist

- [ ] pgvector extension enabled and table created
- [ ] NVIDIA embedding API returns vectors
- [ ] Knowledge base documents chunked and indexed
- [ ] Retriever returns relevant chunks for code-related queries
- [ ] Reviewer's verdicts now cite specific sources from knowledge_base/
- [ ] Feedback loop includes cited sources for Implementer
- [ ] `tests/test_rag.py` passes
- [ ] Integration test with RAG passes
- [ ] All commits follow convention
- [ ] `v0.2.0` tag applied

---

## Files Created / Modified by End of Day 2

| File | Status |
|---|---|
| `rag/setup_db.py` | New |
| `rag/embedder.py` | New |
| `rag/chunker.py` | New |
| `rag/indexer.py` | New |
| `rag/retriever.py` | New |
| `knowledge_base/python-style-guide.md` | New |
| `knowledge_base/code-review-checklist.md` | New |
| `knowledge_base/api-design-standards.md` | New |
| `knowledge_base/general-requirements.md` | New |
| `agents/reviewer.py` | Modified — RAG integration |
| `prompts/reviewer_system.md` | Modified — RAG grounding instructions |
| `orchestrator.py` | Modified — RAG init + enhanced feedback |
| `models.py` | Modified — add RetrievedChunk |
| `tests/test_rag.py` | New |
| `tests/test_rag_integration.py` | New |
