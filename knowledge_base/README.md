# AKILI-SPECS Knowledge Base

This directory contains the curated engineering standards, architectural guidelines, and review checklists utilized by the **Reviewer Agent** to perform grounded, citation-backed audits.

---

## 1. Corpus Documents

| File | Primary Domain | Governing Rules & Standards |
| :--- | :--- | :--- |
| [python-style-guide.md](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/knowledge_base/python-style-guide.md) | Python Code Quality | Type hints (PEP 484), Google-style docstrings, error handling, idiomatic collection usage, concurrency safety. |
| [code-review-checklist.md](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/knowledge_base/code-review-checklist.md) | Code Audit & Correctness | Edge-case validation, exception boundaries, race conditions, resource leaks, complexity, and security checks. |
| [api-design-standards.md](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/knowledge_base/api-design-standards.md) | Interface & API Design | RESTful naming conventions, HTTP status codes, idempotency, rate limiting, and response schemas. |
| [general-requirements.md](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/knowledge_base/general-requirements.md) | System Specifications | Non-functional requirements, schema integrity, constraint checks, and database indexing strategies. |

---

## 2. Ingestion & RAG Indexing Pipeline

1. **Chunking** ([rag/chunker.py](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/rag/chunker.py)):
   - Documents are parsed into semantic sections based on Markdown headers (`#`, `##`, `###`).
   - Chunks maintain section breadcrumb headers for preservation of hierarchical context.
2. **Embedding** ([rag/embedder.py](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/rag/embedder.py)):
   - Generated via NVIDIA's `nvidia/nemotron-3.5-embed-8b` model.
   - Outputs 4,096-dimensional normalized vectors (or truncated 1,024/512 dimensions when configured).
3. **Storage & Search** ([rag/retriever.py](file:///c:/Users/JANARDHAN/OneDrive/Desktop/RAG Agent/rag/retriever.py)):
   - Stored in PostgreSQL table `document_embeddings` via `pgvector` with cosine similarity (`<=>` operator).
   - If `pgvector` native extension is unavailable, an automatic array-based dot-product fallback handles retrieval seamlessly.

---

## 3. Re-indexing the Knowledge Base

To re-index or update the corpus after modifying documents:
```bash
python -m rag.indexer
```
