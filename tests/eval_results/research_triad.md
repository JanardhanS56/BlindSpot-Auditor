# Evaluation Prompt: research (AKILI-SPECS Triad)

**Prompt:**
> Compare the trade-offs between microservices and monolithic architectures for a team of 5 developers building a B2B SaaS product.

**Known Traps:**
- unsourced claims
- absolutist statements

**Expected Triad Advantage:**
Reviewer flags unsourced claims

**Latency:** 40.89s

**Tasks Decomposed:** 1
**Passed Directly:** 0
**Retried & Passed:** 1
**Force Merged:** 0
**Issues Resolved:** 1 / 1

**Grounding References Cited:**
- general best practices – completeness of response
- Fallback evaluator

---

## Generated Output

## Trade‑off Comparison: Microservices vs. Monolithic Architecture  

**Context** – A small team (5 developers) is building a B2B SaaS product that will evolve over time, serve multiple enterprise customers, and require reasonable scalability, reliability, and security.

---

### Comparison Table  

| Dimension | Monolithic Architecture | Microservices Architecture |
|-----------|------------------------|----------------------------|
| **Team Structure & Communication** | Simple – all developers work on a single codebase, easier coordination. | Requires clear service ownership, API contracts, and more cross‑team communication. |
| **Development Speed (Initial Phase)** | Faster to get an MVP up‑and‑running; fewer boiler‑plate projects, shared libraries, and build pipelines. | Slower start – need to set up multiple repositories, CI/CD pipelines, service discovery, and contracts. |
| **Codebase Size & Complexity** | Grows as a single large codebase; risk of tight coupling and “spaghetti” code if not modularized. | Each service stays small and focused, encouraging clean boundaries, but overall system complexity rises (multiple repos, versioning). |
| **Deployment Frequency** | Single deployable artifact; any change requires redeploying the whole app. | Independent deployments per service; can release features or fixes without touching unrelated services. |
| **Scalability** | Scale the whole application (vertical scaling or replicating the whole service). May waste resources if only a subset of functionality
