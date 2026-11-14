# Day 3 Master Prompt — Polish, Parallel Dispatch & Evaluation

> **Paste this prompt into your AI coding assistant on Day 3.**
> It references `PLAN/day3-implementation-plan.md` for the detailed build order.
> **Prerequisite:** Day 2 must be complete — `v0.2.0` tagged, RAG pipeline functional.

---

## MASTER PROMPT

```
You are finishing the AKILI-SPECS multi-agent system. Today is Day 3: Polish,
Parallel Dispatch & Evaluation.

## PROJECT CONTEXT

Days 1 and 2 are complete:
- Day 1 (v0.1.0): MCP server, Leader/Implementer/Reviewer agents, Groq integration,
  orchestrator with sequential dispatch and feedback loop
- Day 2 (v0.2.0): NVIDIA Nemotron-3.5 embeddings, pgvector, knowledge base indexed,
  Reviewer now retrieves and cites RAG sources in verdicts, enhanced feedback loop

Read these files to understand the full system:
1. `PLAN/design.md` — architecture
2. `PLAN/day3-implementation-plan.md` — step-by-step build order for today
3. `PLAN/testing-strategy.md` — evaluation methodology and test prompts
4. `PLAN/expected-outcomes.md` — what "done" looks like, quantitative targets

Also read all existing source files to understand the current implementation:
- `config.py`, `models.py`, `llm_client.py`
- `agents/base.py`, `agents/leader.py`, `agents/implementer.py`, `agents/reviewer.py`
- `rag/embedder.py`, `rag/chunker.py`, `rag/indexer.py`, `rag/retriever.py`
- `orchestrator.py`, `mcp_server.py`
- `prompts/*.md`

## WHAT TO BUILD TODAY

Three pillars:

### Pillar 1: Parallel Performance
- Convert sequential task processing to `asyncio.gather` for concurrent Implementers
- Ensure Implementer is stateless per-call (no shared mutable state)
- Add verdict aggregation (AggregateReport model)
- Enhance Leader merge to include unresolved warnings

### Pillar 2: Production Hardening
- MCP server: timeout handling, graceful degradation, descriptive tool metadata
- Latency optimization options (embedding truncation, top-K tuning)
- Structured progress logging at every pipeline stage
- Error isolation: one task failure doesn't crash the pipeline

### Pillar 3: Evaluation (Proving the Thesis)
- Build single-agent baseline (same model, same prompts, no decomposition)
- Run 5 evaluation prompts through both baseline and triad
- Save results side-by-side in `tests/eval_results/`
- Each eval prompt has known "traps" the triad should catch

## BUILD ORDER

Follow `PLAN/day3-implementation-plan.md` exactly. 13 steps, each with a micro-commit.

## KEY CONSTRAINTS

1. Parallel dispatch must use `asyncio.gather` — not threads
2. Each parallel task runs its own implement → review → retry loop independently
3. Leader merge happens ONLY after all tasks complete
4. Baseline uses the EXACT same Groq model and parameters — only difference is architecture
5. Eval results must be saved as files, not just printed
6. MCP tool description must explain the system to judges (they read it)
7. Timeout: 120s for full pipeline; return partial results on timeout, don't crash

## ACCEPTANCE CRITERIA (verify before tagging v1.0.0)

- [ ] Multiple Implementer tasks run concurrently (timing proves parallelism)
- [ ] AggregateReport shows passed/retried/force-merged counts
- [ ] Force-merged tasks include warnings in final answer
- [ ] Single-agent baseline works on all 5 eval prompts
- [ ] AKILI-SPECS triad works on all 5 eval prompts
- [ ] Eval results saved in tests/eval_results/ (10 files: 5 baseline + 5 triad)
- [ ] MCP server survives: API timeout, pgvector down, malformed prompt
- [ ] MCP tool has clear description for judges
- [ ] Progress log shows full pipeline trace with timing
- [ ] tests/test_integration_final.py passes
- [ ] All commits follow convention
- [ ] v1.0.0 tag applied

## THE HACKATHON QUESTION

Everything today answers: "Does the team beat a single agent working alone?"

The eval results are your proof. For each of the 5 prompts, the triad should:
- Catch traps the baseline misses (edge cases, hallucinations, contradictions)
- Cite specific sources for its review decisions
- Produce a more complete, internally consistent answer

If a prompt shows the baseline winning, that's fine — note it honestly.
The system's value is in STRUCTURAL guarantees (read-only review, RAG grounding),
not in winning every single prompt.

## WHAT NOT TO DO

- Do NOT change the agent architecture (Leader/Implementer/Reviewer separation)
- Do NOT switch models or add new API providers
- Do NOT over-optimize — the eval results matter more than microseconds
- Do NOT skip the baseline comparison — it's the entire judging criteria
- Do NOT fabricate eval results — run them honestly
```

---

## USAGE

1. Ensure Day 2 code is complete and `v0.2.0` is tagged
2. Ensure knowledge base is indexed (`python -m rag.indexer`)
3. Paste the prompt above into your AI coding assistant
4. The assistant reads all referenced files and existing code, then builds Day 3
5. Run `python tests/run_evaluation.py` to generate eval results
6. Review results in `tests/eval_results/`
7. Tag `v1.0.0` when all acceptance criteria pass
8. The system is now judge-ready — `python mcp_server.py` to serve
