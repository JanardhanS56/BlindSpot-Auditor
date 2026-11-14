# Expected Outcomes — AKILI-SPECS

## 1. What "Done" Looks Like

By the end of Day 3, the system should:

1. **Accept any prompt** via MCP server connection
2. **Decompose** the prompt into sub-tasks (Leader)
3. **Generate** code/content for each sub-task in parallel (Implementers)
4. **Audit** each output against RAG-retrieved standards (Reviewer)
5. **Self-correct** via feedback loop (FAIL → re-dispatch with notes, max 3 attempts)
6. **Return a merged final answer** that is factually grounded and internally consistent
7. **Beat a single-agent baseline** on the same prompts, measured blind

---

## 2. Day-by-Day Milestones

### Day 1: Foundation — "It Works End-to-End"

| Milestone | Acceptance Criteria |
|---|---|
| MCP server starts and accepts connections | `mcp_server.py` runs, handles `handle_prompt` tool |
| Leader decomposes a prompt | Given "Build a REST API for a todo app", returns 3+ structured `Task` objects |
| Implementer generates per-task | Given a `Task`, returns a `TaskResult` with code/content |
| Reviewer audits output | Given a `TaskResult`, returns a `Verdict` with pass/fail and issues |
| Orchestrator runs full loop | Prompt → decompose → implement → review → merge → response |
| Groq client works | All 3 agents call Groq API successfully |

**Tag:** `v0.1.0`

### Day 2: RAG-Grounded Review — "It Reviews Against Evidence"

| Milestone | Acceptance Criteria |
|---|---|
| NVIDIA embedder works | Can embed a text chunk and get a 4096-dim vector |
| pgvector stores vectors | `CREATE EXTENSION vector` works; insert + query succeed |
| Indexer ingests knowledge base | All docs in `knowledge_base/` are embedded and stored |
| Retriever returns relevant chunks | Given a review query, returns top-5 relevant chunks |
| Reviewer uses RAG context | Verdict references retrieved documents, not just parametric memory |
| Feedback loop works | FAIL verdict → re-dispatch → Implementer sees reviewer notes |

**Tag:** `v0.2.0`

### Day 3: Polish & Evaluation — "It Beats the Baseline"

| Milestone | Acceptance Criteria |
|---|---|
| Parallel Implementers | Multiple sub-tasks dispatch concurrently via `asyncio.gather` |
| Verdict aggregation | Leader merges only when ALL sub-tasks PASS |
| Force-merge with warnings | After 3 FAILs, merge anyway but include Reviewer's unresolved concerns |
| Single-agent baseline | Same Groq model, same prompts, no decomposition — records results |
| A/B comparison | Side-by-side output quality on 5 test prompts |
| Latency acceptable | End-to-end < 60 seconds for a medium-complexity prompt |
| MCP integration clean | Judges can connect their assistant and drive it with sealed prompts |

**Tag:** `v1.0.0`

---

## 3. Quantitative Targets

| Metric | Single Agent Baseline | AKILI-SPECS Target | Measurement |
|---|---|---|---|
| **Confirmation bias** | ~35% undetected flaws | <5% | Count of issues Reviewer catches that single agent misses |
| **Internal consistency** | Contradictions in ~20% of long outputs | <2% | Leader's task graph prevents contradiction; Reviewer checks |
| **Factual grounding** | Unsourced claims pass freely | 0 unsourced claims | Reviewer's RAG retrieval flags unsupported statements |
| **Context efficiency** | ~60% effective utilization | ~90% | Each agent uses context for its specialty only |
| **Latency** | ~15s (single call) | <60s (full pipeline) | Acceptable 4x cost for quality guarantee |

---

## 4. Demo Scenarios (Test Prompts)

These simulate the range of "five sealed prompts from very different worlds" the judges will use:

### Prompt 1: Code Generation (Software Engineering)
> "Build a Python function that validates credit card numbers using the Luhn algorithm. Include error handling, type hints, and unit tests."

**Expected superiority:** Reviewer catches missing edge cases (empty string, non-numeric input) that single agent overlooks.

### Prompt 2: Research Synthesis (Knowledge Work)
> "Compare the trade-offs between microservices and monolithic architectures for a team of 5 developers building a B2B SaaS product."

**Expected superiority:** Reviewer flags unsourced claims ("microservices are always better for scale") and demands evidence.

### Prompt 3: Multi-Step Reasoning (Logic)
> "A farmer needs to transport a fox, a chicken, and a bag of grain across a river. The boat can carry the farmer and one item. If left alone, the fox eats the chicken and the chicken eats the grain. How does the farmer get everything across?"

**Expected superiority:** Reviewer verifies each step doesn't violate constraints (fox+chicken alone, chicken+grain alone).

### Prompt 4: Creative + Technical (Mixed)
> "Design a database schema for a social media platform that supports posts, comments, likes, and follower relationships. Write the SQL CREATE TABLE statements and explain the indexing strategy."

**Expected superiority:** Separate Implementer handles code, Reviewer checks normalization and index correctness.

### Prompt 5: Adversarial / Hallucination Trap
> "Explain the Robertson-Walker theorem and its implications for distributed systems consensus."

**Expected superiority:** This is a fabricated theorem. Single agent will hallucinate an explanation. Reviewer's RAG search returns nothing → flags as unsupported claim.

---

## 5. Failure Modes & Acceptable Degradation

| Failure Mode | Acceptable? | Handling |
|---|---|---|
| Groq API rate limit | Yes | Exponential backoff; degrade to sequential processing |
| Reviewer too strict (3 FAILs) | Yes | Force-merge with warnings; note unresolved issues |
| RAG returns irrelevant chunks | Acceptable | Reviewer ignores low-similarity results; still has parametric review |
| One Implementer fails | Yes | Retry that sub-task; other results are preserved |
| Latency > 60s | Marginal | Stream partial results; reduce top-K; truncate embeddings |
| pgvector unavailable | Critical | Fall back to in-memory cosine similarity on cached embeddings |

---

## 6. Judge-Facing Deliverables

1. **MCP Server** — judges connect and drive with their prompts
2. **Single-agent baseline** — same model, same prompts, for blind comparison
3. **Quality delta report** — per-prompt comparison showing what the triad caught
4. **Architecture one-pager** — the `design.md` document explains the thesis
5. **Git log** — the commit history tells the development story
