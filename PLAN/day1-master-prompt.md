# Day 1 Master Prompt — Foundation

> **Paste this prompt into your AI coding assistant on Day 1.**
> It references `PLAN/day1-implementation-plan.md` for the detailed build order.

---

## MASTER PROMPT

```
You are building the AKILI-SPECS multi-agent system — a Leader-Implementer-Reviewer
triad exposed as an MCP server. Today is Day 1: Foundation.

## PROJECT CONTEXT

Read these files first (in order):
1. `PLAN/design.md` — full system architecture, data models, component contracts
2. `PLAN/agent-prompts-spec.md` — system prompt specifications for all 3 agents
3. `PLAN/day1-implementation-plan.md` — step-by-step build order for today
4. `PLAN/git-commits-convention.md` — commit format and micro-commit strategy

## WHAT TO BUILD TODAY

Build the foundation: a working end-to-end pipeline where:
- A user prompt enters via MCP server
- The Leader decomposes it into sub-tasks
- The Implementer generates code/content for each sub-task
- The Reviewer audits each output and returns pass/fail verdicts
- The Orchestrator manages the loop: FAIL → re-dispatch (max 3), then merge

NO RAG today — the Reviewer uses only its parametric knowledge. RAG is Day 2.

## TECH STACK

- Python 3.11+
- Groq API for all LLM calls (key in .env as GROQ_API_KEY)
- Pydantic v2 for data models
- httpx for async HTTP
- asyncio for orchestration
- mcp SDK for MCP server
- python-dotenv for config

## BUILD ORDER

Follow `PLAN/day1-implementation-plan.md` exactly. It specifies 16 steps, each
with a micro-commit. Do not skip steps or combine commits.

Step summary:
1.  Scaffold directories + __init__.py files
2.  requirements.txt
3.  config.py — settings loader
4.  models.py — Task, TaskResult, Verdict, Issue, AgentMessage
5.  llm_client.py — async Groq wrapper with retry
6.  agents/base.py — BaseAgent ABC
7.  agents/leader.py — decompose() + merge()
8.  prompts/leader_system.md
9.  agents/implementer.py — generate()
10. prompts/implementer_system.md
11. agents/reviewer.py — audit() (read-only enforced)
12. prompts/reviewer_system.md
13. orchestrator.py — async dispatch + feedback loop
14. mcp_server.py — MCP entry point
15. tests/test_smoke.py — end-to-end smoke test
16. Tag v0.1.0

## COMMIT CONVENTION

Every step = 1 micro-commit. Format:
  <type>(<scope>): <description>

Types: feat, fix, docs, test, chore, decision
Scopes: leader, impl, reviewer, orchestrator, mcp, models, config, prompts, tests

Example: `feat(models): add Task and Verdict pydantic models`

## KEY CONSTRAINTS

1. The Reviewer agent must have NO write capabilities — audit() returns a Verdict, nothing else
2. The Leader must NEVER generate code/content — only decompose and merge
3. All agents use the same Groq model (llama-3.3-70b-versatile) but different system prompts
4. Max 3 retry attempts on FAIL — then force-merge with warnings
5. All Pydantic models must match the schemas in PLAN/design.md § 5

## ACCEPTANCE CRITERIA (verify before tagging v0.1.0)

- [ ] `python mcp_server.py` starts without errors
- [ ] Groq API calls succeed for all 3 agents
- [ ] Leader decomposes "Build a REST API for a todo app" into 3+ tasks
- [ ] Implementer generates code for a task
- [ ] Reviewer returns a structured Verdict (pass or fail with issues)
- [ ] Full pipeline: prompt → decompose → implement → review → merge → response
- [ ] FAIL re-dispatch injects reviewer_notes into the Implementer's next attempt
- [ ] Force-merge after 3 FAILs includes warnings
- [ ] tests/test_smoke.py passes
- [ ] All commits follow convention

## WHAT NOT TO DO

- Do NOT implement RAG, embeddings, or pgvector (that's Day 2)
- Do NOT implement parallel Implementer dispatch (that's Day 3)
- Do NOT over-engineer — this is a hackathon, not production
- Do NOT use feature branches — commit to master with micro-commits
```

---

## USAGE

1. Open your AI coding assistant (Antigravity, Claude, Cursor, etc.)
2. Paste the prompt above
3. The assistant will read the referenced files and build Day 1 step by step
4. Verify each commit matches the convention
5. Run the smoke test at the end
6. Tag `v0.1.0` when all acceptance criteria pass
