# Git Commits Convention — AKILI-SPECS

## 1. Commit Message Format

```
<type>(<scope>): <short description>

<body — optional, for decisions and context>
```

### Types

| Type | When to Use |
|---|---|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code restructure with no behavior change |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `chore` | Dependencies, config, tooling |
| `decision` | Architectural decision recorded (use body for rationale) |
| `wip` | Work in progress checkpoint (squash before merge) |

### Scopes

| Scope | Covers |
|---|---|
| `leader` | Leader agent |
| `impl` | Implementer agent |
| `reviewer` | Reviewer agent |
| `rag` | Embedding, indexing, retrieval |
| `orchestrator` | Task dispatch, feedback loop |
| `mcp` | MCP server entry point |
| `models` | Pydantic data models |
| `config` | Configuration, env, settings |
| `prompts` | System prompts for agents |
| `tests` | Test files |
| `plan` | Planning documents |

---

## 2. Micro-Commit Strategy

Every **logical unit of change** gets its own commit. The goal is a git log that reads like a development journal.

### What Qualifies as a Micro-Commit

| Category | Example Commit |
|---|---|
| **New file** | `feat(models): add Task and Verdict pydantic models` |
| **New function/class** | `feat(leader): implement decompose() method` |
| **Bug fix** | `fix(orchestrator): prevent infinite FAIL loop — cap at 3 retries` |
| **Decision** | `decision(rag): use cosine similarity over dot product — L2-normalized vectors` |
| **Config change** | `chore(config): add NVIDIA_API_KEY to config loader` |
| **Prompt update** | `docs(prompts): refine reviewer system prompt — add hallucination check` |
| **Test addition** | `test(reviewer): verify read-only constraint enforcement` |
| **Dependency** | `chore: add httpx and pydantic to requirements.txt` |

### What Does NOT Get Its Own Commit

- Fixing a typo you just introduced (amend the previous commit)
- Adding a missing import (amend)
- Formatting changes (amend or group with the feature)

---

## 3. Decision Commits

Architectural decisions are committed with type `decision` and a body explaining the rationale. This creates a searchable log of why things are the way they are.

```
decision(rag): choose pgvector over ChromaDB for vector storage

Rationale:
- User already has PostgreSQL running locally
- pgvector is a single CREATE EXTENSION, no new service
- Scales to production unlike in-memory stores
- SQL-native queries for hybrid search later

Alternatives considered:
- ChromaDB: simpler API but adds a new service dependency
- FAISS: fast but no persistence without wrapper
- Pinecone: cloud-hosted, adds latency and cost
```

---

## 4. Commit Frequency by Phase

| Phase | Expected Commits | Cadence |
|---|---|---|
| **Day 1** (Foundation) | 15–20 | Every new file, class, or integration point |
| **Day 2** (RAG + Review) | 10–15 | Every pipeline stage, prompt refinement |
| **Day 3** (Polish + Eval) | 8–12 | Optimization, test results, final decisions |

---

## 5. Branch Strategy

For this hackathon, work on `master` with micro-commits. No feature branches needed — the commit log IS the feature history.

```bash
# Check the development journal anytime
git log --oneline --graph

# Find all decisions
git log --oneline --grep="decision"

# Find all changes to a component
git log --oneline -- agents/reviewer.py
```

---

## 6. Tagging

Tag at the end of each day to mark milestones:

```bash
git tag -a v0.1.0 -m "Day 1 complete: foundation — MCP server, agents, orchestrator"
git tag -a v0.2.0 -m "Day 2 complete: RAG pipeline — embeddings, pgvector, grounded review"
git tag -a v1.0.0 -m "Day 3 complete: polish — parallel dispatch, eval, baseline comparison"
```
