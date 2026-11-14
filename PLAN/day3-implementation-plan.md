# Day 3 Implementation Plan — Polish, Parallel Dispatch & Evaluation

> **Prerequisite:** Day 2 complete (`v0.2.0` tagged). RAG pipeline works, Reviewer cites sources.
> **Goal:** Parallel Implementers, hardened feedback loop, baseline comparison, demo-ready system.

---

## Build Order (Each Step = 1 Micro-Commit)

### Step 1: Parallel Implementer Dispatch
**Commit:** `feat(orchestrator): implement parallel Implementer dispatch with asyncio.gather`

File: `orchestrator.py` (modify existing)
- Change sequential task processing to parallel:
  ```python
  # Before (Day 1 — sequential):
  for task in tasks:
      result = await implementer.generate(task)
      ...

  # After (Day 3 — parallel):
  results = await asyncio.gather(
      *[self._process_task(task) for task in tasks]
  )
  ```
- New method: `async def _process_task(self, task: Task) -> TaskResult`
  - Encapsulates: generate → review → retry loop for a single task
  - Returns the final (PASS'd or force-merged) result
- Error isolation: one task failing doesn't crash others

---

### Step 2: Concurrent Implementer Instances
**Commit:** `feat(impl): support multiple concurrent Implementer instances`

File: `agents/implementer.py` (modify existing)
- Ensure `ImplementerAgent` is stateless per-call (no shared mutable state)
- Each `_process_task` creates its own call context
- Add task ID to all log messages for tracing

---

### Step 3: Verdict Aggregation
**Commit:** `feat(orchestrator): add verdict aggregation — merge only when all tasks PASS`

File: `orchestrator.py` (modify existing)
- New method: `def aggregate_verdicts(self, results: list[tuple[TaskResult, Verdict]]) -> AggregateReport`
- `AggregateReport` model:
  ```python
  class AggregateReport(BaseModel):
      total_tasks: int
      passed: int
      failed_then_passed: int    # Passed after retry
      force_merged: int           # Hit max retries
      total_issues_found: int
      issues_resolved: int
      unresolved_warnings: list[str]
  ```
- Leader receives the `AggregateReport` alongside results for merge context

---

### Step 4: Enhanced Leader Merge
**Commit:** `feat(leader): enhance merge() — include aggregate report and unresolved warnings`

File: `agents/leader.py` (modify existing)
- `merge()` now receives `AggregateReport` alongside results
- If `force_merged > 0`: include a "⚠ Unresolved Concerns" section in the final answer
- Merge prompt instructs the LLM to:
  - Combine all sub-task outputs coherently
  - Note any caveats from force-merged tasks
  - Eliminate redundancy between sub-tasks

---

### Step 5: Latency Optimization
**Commit:** `feat(config): add latency optimization options — embedding truncation, top-K tuning`

File: `config.py` (modify existing)
- Add settings:
  ```python
  EMBEDDING_DIM: int = 4096          # Set to 1024 for faster retrieval
  EMBEDDING_TRUNCATE: bool = False    # Enable to truncate + L2-renormalize
  RAG_TOP_K: int = 5                 # Reduce for lower latency
  RAG_MIN_SIMILARITY: float = 0.3    # Increase to reduce noise
  ```
- If `EMBEDDING_TRUNCATE`: embedder truncates to `EMBEDDING_DIM` and re-normalizes

---

### Step 6: Streaming / Progress Logging
**Commit:** `feat(orchestrator): add structured progress logging for debugging and demo`

File: `orchestrator.py` (modify existing)
- Log at each stage with structured format:
  ```
  [ORCHESTRATOR] Prompt received — decomposing...
  [LEADER] Decomposed into 3 tasks: [task-1, task-2, task-3]
  [IMPLEMENTER] task-1: generating... (attempt 1/3)
  [IMPLEMENTER] task-1: complete (342 tokens)
  [REVIEWER] task-1: reviewing with 5 RAG chunks...
  [REVIEWER] task-1: FAIL — 1 critical issue (unhandled empty input)
  [IMPLEMENTER] task-1: re-generating with reviewer notes... (attempt 2/3)
  [REVIEWER] task-1: PASS — 0 issues
  [LEADER] All tasks passed — merging final answer...
  [ORCHESTRATOR] Complete — 3 tasks, 1 retry, 0 force-merges, 47.2s total
  ```
- Also track timing per stage for performance analysis

---

### Step 7: Single-Agent Baseline
**Commit:** `feat(tests): implement single-agent baseline for A/B comparison`

File: `tests/test_baseline.py`
- Class `SingleAgentBaseline`:
  - Same Groq model (`llama-3.3-70b-versatile`)
  - Same temperature and parameters
  - Simple system prompt: "You are a helpful assistant."
  - Method: `async def run(self, prompt: str) -> str`
  - No decomposition, no review, just direct LLM call
- Method: `async def compare(self, prompt: str) -> ComparisonResult`
  - Runs both baseline and triad on same prompt
  - Returns both outputs side by side

---

### Step 8: Evaluation Prompts
**Commit:** `test: add 5 evaluation prompts with expected traps`

File: `tests/eval_prompts.json`
```json
[
  {
    "id": "code-gen",
    "prompt": "Build a Python function that validates credit card numbers using the Luhn algorithm. Include error handling, type hints, and unit tests.",
    "traps": ["empty string input", "non-numeric characters", "single digit edge case"],
    "expected_triad_advantage": "Reviewer catches missing edge cases"
  },
  {
    "id": "research",
    "prompt": "Compare the trade-offs between microservices and monolithic architectures for a team of 5 developers building a B2B SaaS product.",
    "traps": ["unsourced claims", "absolutist statements"],
    "expected_triad_advantage": "Reviewer flags unsourced claims"
  },
  {
    "id": "logic",
    "prompt": "A farmer needs to transport a fox, a chicken, and a bag of grain across a river. The boat can carry the farmer and one item. If left alone, the fox eats the chicken and the chicken eats the grain. How does the farmer get everything across?",
    "traps": ["leaving fox+chicken alone", "leaving chicken+grain alone"],
    "expected_triad_advantage": "Reviewer validates each step against constraints"
  },
  {
    "id": "mixed",
    "prompt": "Design a database schema for a social media platform that supports posts, comments, likes, and follower relationships. Write the SQL CREATE TABLE statements and explain the indexing strategy.",
    "traps": ["missing foreign keys", "no indexes on lookup columns"],
    "expected_triad_advantage": "Separate implementation and review catches schema issues"
  },
  {
    "id": "hallucination",
    "prompt": "Explain the Robertson-Walker theorem and its implications for distributed systems consensus.",
    "traps": ["fabricated theorem — should flag uncertainty"],
    "expected_triad_advantage": "RAG returns nothing — Reviewer flags as unsupported"
  }
]
```

---

### Step 9: Run Evaluation
**Commit:** `test: run full evaluation — 5 prompts, baseline vs triad comparison`

File: `tests/run_evaluation.py`
- For each prompt in `eval_prompts.json`:
  1. Run through single-agent baseline → save output
  2. Run through AKILI-SPECS triad → save output + metadata (retries, verdicts, RAG refs)
  3. Save both to `tests/eval_results/` as separate files
- Output summary table

---

### Step 10: MCP Server Hardening
**Commit:** `fix(mcp): add error handling, timeout, and graceful degradation to MCP server`

File: `mcp_server.py` (modify existing)
- Add timeout for full pipeline (default 120s)
- If timeout: return partial results with explanation
- If Groq API fails: return error message, don't crash
- If pgvector unavailable: fall back to review without RAG, log warning
- Add MCP tool description that explains the system to judges

---

### Step 11: MCP Tool Description
**Commit:** `docs(mcp): add descriptive tool metadata for judge-facing MCP interface`

File: `mcp_server.py` (modify existing)
- Tool name: `handle_prompt`
- Description:
  ```
  AKILI-SPECS Multi-Agent Code Quality System.

  Processes your prompt through a Leader-Implementer-Reviewer triad:
  1. Leader decomposes the prompt into sub-tasks
  2. Implementers generate code/content in parallel
  3. An independent Reviewer audits each output against retrieved standards
  4. Failed outputs are revised based on specific feedback (max 3 attempts)
  5. Leader merges all approved outputs into a final answer

  The Reviewer is architecturally read-only — it cannot modify code, only judge it.
  Reviews are grounded in a RAG knowledge base of coding standards and best practices.
  ```

---

### Step 12: Final Integration Test
**Commit:** `test: add comprehensive integration test — parallel dispatch, RAG review, full pipeline`

File: `tests/test_integration_final.py`
- Test: complex prompt that requires 3+ sub-tasks
- Assert: tasks executed in parallel (timing check — faster than sequential)
- Assert: Reviewer cited RAG sources
- Assert: Final answer is coherent and addresses all parts of the prompt
- Assert: Metadata shows aggregate report

---

### Step 13: Day 3 Tag
```bash
git tag -a v1.0.0 -m "v1.0.0: AKILI-SPECS complete — parallel dispatch, RAG review, baseline eval"
```

---

## Day 3 Acceptance Checklist

- [ ] Parallel Implementer dispatch works (multiple tasks run concurrently)
- [ ] Verdict aggregation reports total/passed/retried/force-merged
- [ ] Leader merge includes unresolved warnings from force-merged tasks
- [ ] Single-agent baseline produces outputs for all 5 eval prompts
- [ ] AKILI-SPECS triad produces outputs for all 5 eval prompts
- [ ] Eval results saved in `tests/eval_results/`
- [ ] MCP server handles errors gracefully (timeout, API failure)
- [ ] MCP tool has descriptive metadata for judges
- [ ] Progress logging shows full pipeline trace
- [ ] tests/test_integration_final.py passes
- [ ] All commits follow convention
- [ ] `v1.0.0` tag applied

---

## Files Created / Modified by End of Day 3

| File | Status |
|---|---|
| `orchestrator.py` | Modified — parallel dispatch, aggregation, progress logging |
| `agents/implementer.py` | Modified — concurrent-safe |
| `agents/leader.py` | Modified — enhanced merge with aggregate report |
| `models.py` | Modified — add AggregateReport |
| `config.py` | Modified — latency optimization settings |
| `mcp_server.py` | Modified — error handling, tool description |
| `tests/test_baseline.py` | New |
| `tests/eval_prompts.json` | New |
| `tests/run_evaluation.py` | New |
| `tests/test_integration_final.py` | New |
| `tests/eval_results/` | New (generated output) |
