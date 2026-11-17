# Evaluation Prompt: research (Single-Agent Baseline)

**Prompt:**
> Compare the trade-offs between microservices and monolithic architectures for a team of 5 developers building a B2B SaaS product.

**Known Traps:**
- unsourced claims
- absolutist statements

**Latency:** 4.54s

---

## Generated Output

## TL;DR  

| Aspect | Monolith (single code‑base, single deployable) | Micro‑services (many small, independently‑deployed services) |
|--------|-----------------------------------------------|--------------------------------------------------------------|
| **Speed of initial delivery** | Very fast – one repo, one CI pipeline, one deployment target. | Slower – you must set up service scaffolding, inter‑service communication, multiple pipelines. |
| **Team coordination** | Simple – 5 developers can share the same repo, branch strategy, and local dev environment. | More complex – you need clear service boundaries, ownership rules, and a “service‑catalog” to avoid stepping on each other’s toes. |
| **Operational overhead** | Low – one container/VM, one DB, one monitoring stack. | High – service discovery, API gateways, distributed tracing, multiple DBs, versioning, network reliability. |
| **Scalability** | Coarse‑grained – you scale the whole app (or use read‑replicas). | Fine‑grained – you can scale hot components (e.g., billing, analytics) independently. |
| **Fault isolation** | A bug or memory leak can bring the whole app down. | Failure is contained to the offending service (if you design for resilience). |
| **Technology heterogeneity** | Usually one language/framework stack. | Each service can use the best language/tool for its problem (but adds cognitive load). |
| **Testing & CI** | Straightforward unit/integration tests; one build artifact. | Need contract testing, end‑to‑end tests across services, multiple build artifacts. |
| **Data consistency** | Single relational schema, ACID transactions are easy. | Distributed data – eventual consistency, saga patterns, or separate DB per service. |
| **Cost (infrastructure & ops)** | Lower – one host/cluster, fewer licenses, less monitoring. | Higher – many hosts/containers, more network traffic, more tooling. |
| **When it shines** | Small teams, early‑stage product, rapid iteration, simple domain. | Large teams, complex domain with clear bounded contexts, need for independent scaling or compliance isolation. |

---

## 1.  Context: 5‑person team building a B2B SaaS product  

| Characteristic | Why it matters |
|----------------|----------------|
| **Team size** – 5 devs (likely 1‑2 front‑end, 2‑3 back‑end, maybe a DevOps/QA “hat”) | Small teams benefit from low coordination overhead. |
| **B2B SaaS** – multi‑tenant, subscription billing, integrations (webhooks, APIs), compliance (e.g., GDPR, SOC‑2) | You’ll need a solid data model, secure APIs, and the ability to evolve features without breaking existing customers. |
| **Growth expectations** – you may need to handle more tenants, higher traffic, or add new modules (analytics, AI, marketplace) later. | Architecture should allow you to start fast but not become a “technical debt” nightmare. |
| **Release cadence** – likely weekly or bi‑weekly releases to stay competitive. | Fast CI/CD pipelines are essential. |
| **Budget / Ops resources** – limited ops staff, probably using a managed cloud provider (AWS, GCP, Azure). | Simpler operational footprints are cheaper. |

---

## 2.  Monolithic Architecture – What It Looks Like

```
src/
 ├─ api/            (REST/GraphQL controllers)
 ├─ services/       (business logic)
 ├─ repository/     (data access)
 ├─ domain/         (entities, value objects)
 └─ config/
Dockerfile
docker-compose.yml
```

*All code lives in a single repository, built into one Docker image (or a single VM).*

### 2.1 Advantages for a 5‑person team

| Benefit | Reason |
|--------|--------|
| **Rapid onboarding** – one repo, one local dev stack (e.g., `docker-compose up`). | New hires can be productive in a day. |
| **Unified testing** – one test suite, one CI pipeline. | Less configuration, fewer flaky builds. |
| **Simpler deployment** – one artifact, one Kubernetes Deployment/Elastic Beanstalk app. | Fewer moving parts to monitor. |
| **Easier data modeling** – single relational DB, ACID transactions across the whole domain. | Billing, tenant isolation, and audit logs are straightforward. |
| **Lower operational cost** – one host/cluster, one monitoring dashboard. | Fits a small budget. |
| **Consistent coding standards** – one language/framework (e.g., Node.js + TypeScript, or Python + Django). | Reduces cognitive load. |

### 2.2 Drawbacks / Risks

| Issue | Impact |
|-------|--------|
| **Coarse scaling** – you must scale the whole app even if only the “reporting” module is hot. | Higher cloud cost under load spikes. |
| **Fault propagation** – a memory leak or runaway query can bring down all tenants. | Potential SLA breach. |
| **Longer build times** – as the codebase grows, CI builds become slower. | Slower feedback loop. |
| **Harder to adopt new tech** – swapping a single component to a different language requires a full rewrite. | Limits experimentation. |
| **Team bottlenecks** – multiple developers editing the same codebase can cause merge conflicts and “ownership” friction. | Slows feature velocity. |
| **Monolithic deployment risk** – a single bad commit can affect every tenant. | Requires robust feature‑flagging and canary releases. |

---

## 3.  Micro‑services Architecture – What It Looks Like

```
/service‑billing/
   Dockerfile, src/, tests/
   helm chart/
   CI pipeline (billing.yml)
/service‑analytics/
   …
/gateway/
   API‑gateway (e.g., Kong, Envoy, AWS API GW)
```

*Each service owns its own repository, its own database (or schema), and its own CI/CD pipeline.*

### 3.1 Advantages for a 5‑person team (when they matter)

| Benefit | Reason |
|--------|--------|
| **Independent scaling** – spin up extra instances of “billing” without touching “auth”. | Cost‑effective for uneven load patterns. |
| **Fault isolation**
