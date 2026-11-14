# Day 1 Implementation Plan — Foundation

> **Goal:** A working end-to-end pipeline: MCP server → Leader → Implementer → Reviewer → response.
> No RAG yet. Basic agents with Groq. The loop works.

---

## Build Order (Each Step = 1 Micro-Commit)

### Step 1: Project Scaffold
**Commit:** `chore: scaffold project directory structure`

Create all directories and `__init__.py` files:
```
agents/__init__.py
rag/__init__.py
prompts/       (empty dir with .gitkeep)
knowledge_base/ (empty dir with README.md)
tests/__init__.py
```

---

### Step 2: Requirements
**Commit:** `chore: add requirements.txt with core dependencies`

```
# requirements.txt
fastapi>=0.100.0
uvicorn>=0.23.0
httpx>=0.25.0
pydantic>=2.0.0
python-dotenv>=1.0.0
groq>=0.4.0
mcp>=1.0.0
asyncio-extras>=1.3.0
```

---

### Step 3: Configuration
**Commit:** `feat(config): add settings loader from .env`

File: `config.py`
- Load `.env` using `python-dotenv`
- Expose: `GROQ_API_KEY`, `NVIDIA_API_KEY`, `POSTGRES_*` (for Day 2)
- Constants: `MAX_RETRIES = 3`, `DEFAULT_MODEL = "llama-3.3-70b-versatile"`, `TOP_K = 5`
- Pydantic `Settings` class with validation

---

### Step 4: Data Models
**Commit:** `feat(models): add Task, TaskResult, Verdict, Issue, AgentMessage pydantic models`

File: `models.py`
- `Task`: id, description, requirements, context, priority, attempt, reviewer_notes
- `TaskResult`: task_id, content, diff, metadata
- `Verdict`: task_id, passed, issues, references, confidence, summary
- `Issue`: severity (critical/major/minor/style), description, location, suggestion
- `AgentMessage`: sender, recipient, payload, timestamp
- All with validators and sensible defaults

---

### Step 5: Groq LLM Client
**Commit:** `feat(config): add Groq LLM client wrapper with async support`

File: `llm_client.py`
- Async wrapper around `groq.AsyncGroq`
- Method: `async def chat(system_prompt: str, user_message: str, model: str = DEFAULT_MODEL) -> str`
- Error handling: retry on rate limit (exponential backoff, max 3)
- Token usage tracking in metadata
- Temperature control parameter

---

### Step 6: Base Agent
**Commit:** `feat(agents): add BaseAgent abstract class`

File: `agents/base.py`
- ABC with: `name`, `system_prompt`, `llm_client`
- Abstract method: `async def run(self, input_data: Any) -> Any`
- Shared logging setup
- Prompt loading from `prompts/` directory

---

### Step 7: Leader Agent
**Commit:** `feat(leader): implement LeaderAgent with decompose() and merge() methods`

File: `agents/leader.py`
- Inherits `BaseAgent`
- `async def decompose(self, prompt: str) -> list[Task]`:
  - Sends prompt to LLM with leader system prompt
  - Parses structured JSON output into `Task` objects
  - Validates each task has requirements and description
- `async def merge(self, results: list[TaskResult]) -> str`:
  - Sends all results to LLM for coherent combination
  - Includes warnings from force-merged tasks
- System prompt loaded from `prompts/leader_system.md`

---

### Step 8: Leader System Prompt
**Commit:** `docs(prompts): add leader system prompt`

File: `prompts/leader_system.md`
- Role definition: planner and coordinator only
- Output format spec (JSON with tasks array)
- Rules: don't generate content, keep tasks independent, clear acceptance criteria
- Merge instructions: eliminate redundancy, preserve caveats

---

### Step 9: Implementer Agent
**Commit:** `feat(impl): implement ImplementerAgent with generate() method`

File: `agents/implementer.py`
- Inherits `BaseAgent`
- `async def generate(self, task: Task) -> TaskResult`:
  - Builds prompt from task description + requirements + reviewer_notes (if retry)
  - Calls LLM
  - Wraps output in `TaskResult`
  - Tracks attempt number and changes from previous
- System prompt loaded from `prompts/implementer_system.md`

---

### Step 10: Implementer System Prompt
**Commit:** `docs(prompts): add implementer system prompt`

File: `prompts/implementer_system.md`
- Role: produce code/content for the assigned sub-task only
- Rules: don't self-review, include type hints, address reviewer notes on retry
- Output format spec

---

### Step 11: Reviewer Agent
**Commit:** `feat(reviewer): implement ReviewerAgent with audit() method — read-only enforced`

File: `agents/reviewer.py`
- Inherits `BaseAgent`
- `async def audit(self, task: Task, result: TaskResult) -> Verdict`:
  - Builds prompt from: original task + implementer output
  - Calls LLM with reviewer system prompt
  - Parses structured JSON into `Verdict`
  - Validates: critical/major issues → `passed = False`
- **No write tools** — the class has no methods that modify state
- Day 2 will add: RAG context injection before LLM call

---

### Step 12: Reviewer System Prompt
**Commit:** `docs(prompts): add reviewer system prompt`

File: `prompts/reviewer_system.md`
- Role: audit only, cannot modify
- Severity definitions
- PASS criteria: zero critical or major issues
- Output format spec (Verdict JSON)
- Rules: check edge cases, flag unsupported claims, provide actionable suggestions

---

### Step 13: Orchestrator
**Commit:** `feat(orchestrator): implement async orchestrator with dispatch and feedback loop`

File: `orchestrator.py`
- Class `Orchestrator`:
  - Holds references to Leader, Implementer, Reviewer
  - `async def run(self, prompt: str) -> str`:
    1. `tasks = await leader.decompose(prompt)`
    2. For each task (sequentially in Day 1, parallel in Day 3):
       - `result = await implementer.generate(task)`
       - `verdict = await reviewer.audit(task, result)`
       - If FAIL and attempt < 3: inject reviewer_notes, increment attempt, re-dispatch
       - If FAIL and attempt >= 3: force-merge with warnings
       - If PASS: collect result
    3. `final = await leader.merge(passed_results)`
    4. Return final answer
  - Logging at each stage

---

### Step 14: MCP Server
**Commit:** `feat(mcp): implement MCP server with handle_prompt tool`

File: `mcp_server.py`
- Uses `mcp` SDK to create an MCP server
- Exposes tool: `handle_prompt(prompt: str) -> str`
  - Creates Orchestrator instance
  - Calls `orchestrator.run(prompt)`
  - Returns final answer
- Configurable transport (stdio for local testing)
- Entry point: `python mcp_server.py`

---

### Step 15: Integration Smoke Test
**Commit:** `test: add end-to-end smoke test for full pipeline`

File: `tests/test_smoke.py`
- Test: send "Write a hello world function in Python" through the full pipeline
- Assert: response contains a function definition
- Assert: all 3 agents were invoked (check logs)

---

### Step 16: Day 1 Tag
**Commit:** (none — just tag)
```bash
git tag -a v0.1.0 -m "Day 1: foundation — MCP server, agents, orchestrator, Groq integration"
```

---

## Day 1 Acceptance Checklist

- [ ] `python mcp_server.py` starts without errors
- [ ] Groq API calls succeed for all 3 agents
- [ ] Leader decomposes a prompt into structured tasks
- [ ] Implementer generates content for a task
- [ ] Reviewer returns a pass/fail verdict
- [ ] Orchestrator runs the full loop
- [ ] FAIL re-dispatch works (reviewer notes injected)
- [ ] Force-merge after 3 failures works
- [ ] All code committed with micro-commits
- [ ] `v0.1.0` tag applied

---

## Files Created by End of Day 1

| File | Status |
|---|---|
| `config.py` | New |
| `models.py` | New |
| `llm_client.py` | New |
| `agents/__init__.py` | New |
| `agents/base.py` | New |
| `agents/leader.py` | New |
| `agents/implementer.py` | New |
| `agents/reviewer.py` | New |
| `orchestrator.py` | New |
| `mcp_server.py` | New |
| `prompts/leader_system.md` | New |
| `prompts/implementer_system.md` | New |
| `prompts/reviewer_system.md` | New |
| `requirements.txt` | New |
| `tests/test_smoke.py` | New |
