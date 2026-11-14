import asyncio
import pytest
from rag.embedder import NvidiaEmbedder
from rag.indexer import KnowledgeBaseIndexer
from rag.retriever import KnowledgeRetriever
from rag.setup_db import get_connection, setup_database


@pytest.mark.asyncio
async def test_embedder_dimensions():
    """Verify NvidiaEmbedder produces a 4096-dimensional normalized vector."""
    embedder = NvidiaEmbedder()
    vec = await embedder.embed("Test text for embedding", input_type="query")
    assert isinstance(vec, list)
    assert len(vec) == 4096
    # Verify vector has non-zero values
    magnitude = sum(x * x for x in vec)
    assert 0.99 <= magnitude <= 1.01  # L2 normalized


@pytest.mark.asyncio
async def test_indexer_stores_chunks():
    """Verify KnowledgeBaseIndexer indexes documents and populates the database."""
    setup_database()
    indexer = KnowledgeBaseIndexer()
    total = await indexer.index_all()
    assert total > 0, "Indexer should have indexed at least 1 chunk"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM document_embeddings;")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()

    assert count >= total, f"Expected at least {total} rows in DB, got {count}"


@pytest.mark.asyncio
async def test_retriever_query_and_threshold():
    """Verify KnowledgeRetriever returns relevant chunks and respects top_k & min_similarity."""
    retriever = KnowledgeRetriever(min_similarity=0.2)
    query = "error handling conventions and exceptions"
    results = await retriever.retrieve(query, top_k=3)

    assert len(results) > 0, "Retriever should return matches for error handling"
    assert len(results) <= 3, f"Expected at most 3 results, got {len(results)}"

    for chunk in results:
        assert chunk.content
        assert chunk.source_file
        assert chunk.similarity >= 0.2
        assert 0.0 <= chunk.similarity <= 1.0

    # Test top_k limiting
    single_res = await retriever.retrieve(query, top_k=1)
    assert len(single_res) == 1

    # Test high threshold filters out low matches
    empty_res = await retriever.retrieve("completely unrelated quantum teleportation string", min_similarity=0.95)
    assert len(empty_res) == 0
