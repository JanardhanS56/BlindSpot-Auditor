# Day 2 Master Prompt — RAG-Grounded Review

> **Paste this prompt into your AI coding assistant on Day 2.**
> It references `PLAN/day2-implementation-plan.md` for the detailed build order.
> **Prerequisite:** Day 1 must be complete — `v0.1.0` tagged, all agents functional.

---

## MASTER PROMPT

```
You are continuing to build the AKILI-SPECS multi-agent system. Today is Day 2:
RAG-Grounded Review.

## PROJECT CONTEXT

The Day 1 foundation is complete:
- MCP server, Leader, Implementer, Reviewer agents all work
- Groq API integration working
- Orchestrator runs the full decompose → implement → review → merge loop
- All code is in the project root

Read these files to understand the existing codebase:
1. `PLAN/design.md` — architecture (focus on §4.4 RAG Pipeline and §7 Design Decisions)
2. `PLAN/agent-prompts-spec.md` — Reviewer prompt spec (§3 — focus on RAG grounding rules)
3. `PLAN/day2-implementation-plan.md` — step-by-step build order for today
4. `model_card.md` — NVIDIA Nemotron-3.5-Embed-8B specs (embedding dimensions, input types)

Also read the existing codebase files to understand the current state:
- `config.py`, `models.py`, `llm_client.py`
- `agents/base.py`, `agents/leader.py`, `agents/implementer.py`, `agents/reviewer.py`
- `orchestrator.py`, `mcp_server.py`
- `prompts/reviewer_system.md`

## WHAT TO BUILD TODAY

Add the RAG pipeline so the Reviewer grounds its verdicts in retrieved evidence:

1. **pgvector setup** — enable extension, create embeddings table with IVFFlat index
2. **NVIDIA embedding client** — call Nemotron-3.5-Embed-8B API for 4096-dim vectors
3. **Text chunker** — split knowledge base docs into retrievable chunks
4. **Knowledge base** — seed documents (style guides, coding standards, review checklists)
5. **Indexer** — embed all knowledge base chunks → store in pgvector
6. **Retriever** — query pgvector with cosine similarity → return top-K chunks
7. **Reviewer integration** — inject retrieved chunks into Reviewer's context before each verdict
8. **Enhanced feedback loop** — re-dispatch notes now include cited sources

## TECH DETAILS

### NVIDIA API
- Endpoint: `https://integrate.api.nvidia.com/v1/embeddings`
- Model: `nvidia/nemotron-3.5-embed-8b-bf16` (or the model name from the API docs)
- Auth: `Authorization: Bearer {NVIDIA_API_KEY}` (from .env)
- Input type: `"passage"` for documents, `"query"` for queries
- Output: 4096-dim vector, L2-normalized

### pgvector
- Extension on existing PostgreSQL (credentials in .env)
- Table: `document_embeddings` with `vector(4096)` column
- Index: IVFFlat with `vector_cosine_ops`, lists=10
- Query: `ORDER BY embedding <=> query_vector LIMIT top_k`

### Chunking Strategy
- Split markdown on `## ` headers first
- Fallback: paragraph boundaries (double newline)
- Chunk size: ~1000 chars with 200 char overlap
- Each chunk retains source file name and section header

## BUILD ORDER

Follow `PLAN/day2-implementation-plan.md` exactly. 13 steps, each with a micro-commit.

## KEY CONSTRAINTS

1. The Reviewer still CANNOT write — RAG only adds read context
2. Retrieved chunks are INJECTED into the Reviewer's prompt, not processed separately
3. The Reviewer must CITE specific retrieved sources in its Verdict.references[]
4. If retrieval returns nothing relevant, Reviewer proceeds with parametric review but notes it
5. Embedding dimension: 4096 (truncate to 1024 only if latency is an issue)
6. Minimum similarity threshold: 0.3 (filter out irrelevant results)

## ACCEPTANCE CRITERIA (verify before tagging v0.2.0)

- [ ] `CREATE EXTENSION vector` succeeds on local Postgres
- [ ] NVIDIA API returns a 4096-dim vector for a test string
- [ ] 4 knowledge base documents chunked and indexed in pgvector
- [ ] Retriever returns relevant chunks for "error handling conventions"
- [ ] Reviewer's Verdict now has non-empty `references` citing knowledge_base sources
- [ ] Re-dispatch notes include the specific cited standard the Implementer must comply with
- [ ] tests/test_rag.py passes
- [ ] tests/test_rag_integration.py passes
- [ ] Full pipeline still works end-to-end (no regression)
- [ ] All commits follow convention

## WHAT NOT TO DO

- Do NOT implement parallel Implementers (Day 3)
- Do NOT add more than 4-5 knowledge base docs — enough to prove the concept
- Do NOT fine-tune the embedding model — use it as-is via API
- Do NOT switch to a different vector store — pgvector is the choice
- Do NOT change the Groq model or agent structure from Day 1
```

---

## USAGE

1. Ensure Day 1 code is complete and `v0.1.0` is tagged
2. Ensure PostgreSQL is running locally with the credentials in `.env`
3. Paste the prompt above into your AI coding assistant
4. The assistant reads the referenced files and builds Day 2 step by step
5. Run `python -m rag.indexer` to index the knowledge base
6. Run tests to verify
7. Tag `v0.2.0` when all acceptance criteria pass
