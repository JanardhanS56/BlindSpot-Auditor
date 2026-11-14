# Testing Strategy — AKILI-SPECS

## 1. Testing Philosophy

The hackathon's evaluation is **blind comparison** against a single-agent baseline. Our testing must prove the triad is better, not just different.

We test at three levels:
1. **Unit** — each component works in isolation
2. **Integration** — the pipeline flows correctly end-to-end
3. **Evaluation** — output quality comparison against baseline

---

## 2. Unit Tests

### 2.1 Agent Tests (`tests/test_agents.py`)

| Test | What It Verifies |
|---|---|
| `test_leader_decompose_simple` | Single-task prompt → 1 task |
| `test_leader_decompose_complex` | Multi-part prompt → N tasks with requirements |
| `test_leader_decompose_returns_valid_json` | Output parses into `List[Task]` |
| `test_leader_merge_combines_results` | Multiple `TaskResult`s → single coherent output |
| `test_leader_merge_includes_warnings` | Force-merged tasks include warning notes |
| `test_implementer_generates_content` | Given a `Task`, returns non-empty `TaskResult` |
| `test_implementer_addresses_reviewer_notes` | Re-dispatched task with notes → content changes |
| `test_reviewer_catches_obvious_bug` | Code with division by zero → FAIL verdict |
| `test_reviewer_passes_clean_code` | Correct code → PASS verdict |
| `test_reviewer_is_read_only` | Reviewer has no write tools in its tool list |
| `test_reviewer_returns_valid_verdict` | Output parses into `Verdict` model |

### 2.2 RAG Tests (`tests/test_rag.py`)

| Test | What It Verifies |
|---|---|
| `test_embedder_returns_vector` | Text input → 4096-dim float list |
| `test_embedder_vector_normalized` | L2 norm ≈ 1.0 |
| `test_indexer_stores_and_retrieves` | Index a doc → query returns it |
| `test_retriever_top_k` | Returns exactly K results |
| `test_retriever_relevance` | Query "error handling" returns error-handling doc, not unrelated |
| `test_truncated_embeddings` | 1024-dim truncation still produces valid retrieval |

### 2.3 Orchestrator Tests (`tests/test_orchestrator.py`)

| Test | What It Verifies |
|---|---|
| `test_full_pipeline_simple` | Prompt → final answer (end-to-end) |
| `test_fail_triggers_redispatch` | Reviewer FAIL → Implementer gets reviewer_notes |
| `test_max_retries_force_merges` | 3 FAILs → force-merge with warnings |
| `test_parallel_dispatch` | Multiple tasks run concurrently (timing check) |
| `test_all_pass_before_merge` | Leader waits for all PASS verdicts before merge |

---

## 3. Integration Tests

### 3.1 MCP Server Test

```python
# Simulate judge connecting their assistant
async def test_mcp_server_handles_prompt():
    """Connect to MCP server, send a prompt, get a response."""
    # 1. Start MCP server
    # 2. Connect as client
    # 3. Call handle_prompt with a test prompt
    # 4. Assert response is non-empty and well-formed
    # 5. Assert response was produced by the triad (check logs/metadata)
```

### 3.2 End-to-End Pipeline Test

```python
async def test_end_to_end_with_known_prompt():
    """Full pipeline with a prompt whose expected output is known."""
    prompt = "Write a Python function to check if a string is a palindrome."
    result = await orchestrator.run(prompt)

    # Basic quality checks
    assert "def " in result.content          # Contains a function
    assert "palindrome" in result.content.lower()
    assert result.metadata["reviewer_passed"] == True
    assert result.metadata["attempts"] <= 3
```

---

## 4. Baseline Comparison (The Core Evaluation)

### 4.1 Setup

```python
# tests/test_baseline.py

async def run_baseline(prompt: str) -> str:
    """Single agent, same model, same prompt — no decomposition."""
    response = await groq_client.chat(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.content

async def run_triad(prompt: str) -> str:
    """Full AKILI-SPECS pipeline."""
    return await orchestrator.run(prompt)
```

### 4.2 Evaluation Criteria

Each output is scored on 5 dimensions (1–5 scale):

| Dimension | What It Measures |
|---|---|
| **Correctness** | Is the answer factually and logically correct? |
| **Completeness** | Does it address all parts of the prompt? |
| **Consistency** | Are there internal contradictions? |
| **Groundedness** | Are claims supported or fabricated? |
| **Quality** | Code style, readability, documentation |

### 4.3 Evaluation Method

1. Run both baseline and triad on 5 test prompts
2. Collect outputs in `tests/eval_results/`
3. Score each output on the 5 dimensions
4. Compare aggregate scores

### 4.4 Test Prompts (`tests/eval_prompts.json`)

```json
[
  {
    "id": "code-gen",
    "prompt": "Build a Python function that validates credit card numbers using the Luhn algorithm. Include error handling, type hints, and unit tests.",
    "traps": ["empty string input", "non-numeric characters", "edge case: single digit"]
  },
  {
    "id": "research",
    "prompt": "Compare microservices vs monolithic architectures for a 5-person team building B2B SaaS.",
    "traps": ["unsourced claims", "absolutist statements like 'always better'"]
  },
  {
    "id": "logic",
    "prompt": "A farmer needs to transport a fox, a chicken, and a bag of grain across a river...",
    "traps": ["leaving fox+chicken alone", "leaving chicken+grain alone"]
  },
  {
    "id": "mixed",
    "prompt": "Design a database schema for a social media platform with posts, comments, likes, followers. Write SQL and explain indexing.",
    "traps": ["missing foreign keys", "no indexing on lookup columns"]
  },
  {
    "id": "hallucination",
    "prompt": "Explain the Robertson-Walker theorem and its implications for distributed systems consensus.",
    "traps": ["fabricated theorem — should refuse or flag uncertainty"]
  }
]
```

---

## 5. Regression Testing

After each day's changes, re-run the full test suite:

```bash
# Unit + integration
pytest tests/ -v

# Baseline comparison (manual review)
python -m tests.test_baseline
```

---

## 6. What We're Proving

The tests collectively prove three things:

1. **The triad catches what a single agent misses** (baseline comparison on traps)
2. **The Reviewer is genuinely independent** (read-only enforcement, RAG grounding)
3. **The system is robust** (retry logic, force-merge, error handling)

These map directly to the hackathon's question: *"Does the team beat a single agent working alone?"*
