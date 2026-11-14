import asyncio
import logging
from typing import Any
import psycopg2
import config
from models import RetrievedChunk
from rag.embedder import NvidiaEmbedder
from rag.setup_db import get_connection, setup_database

logger = logging.getLogger("rag.retriever")


def dot_product(v1: list[float], v2: list[float]) -> float:
    """Computes cosine similarity between two unit vectors (dot product)."""
    return sum(a * b for a, b in zip(v1, v2))


class KnowledgeRetriever:
    """Retrieves relevant knowledge base chunks using dense vector similarity."""

    def __init__(
        self,
        embedder: NvidiaEmbedder | None = None,
        default_top_k: int = config.TOP_K,
        min_similarity: float = 0.3,
    ):
        self.embedder = embedder or NvidiaEmbedder()
        self.default_top_k = default_top_k
        self.min_similarity = min_similarity
        self._has_vector_ext: bool | None = None

    def _check_vector_ext(self) -> bool:
        if self._has_vector_ext is None:
            self._has_vector_ext = setup_database()
        return self._has_vector_ext

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        min_similarity: float | None = None,
    ) -> list[RetrievedChunk]:
        """Embeds query and retrieves top-k matching chunks from pgvector."""
        limit = top_k or self.default_top_k
        threshold = min_similarity if min_similarity is not None else self.min_similarity

        # Step 1: Embed query as "query" input type
        query_vector = await self.embedder.embed(query, input_type="query")

        has_ext = self._check_vector_ext()
        conn = get_connection()
        cur = conn.cursor()

        chunks: list[RetrievedChunk] = []

        if has_ext:
            sql = """
            SELECT content, source_file, chunk_index,
                   1 - (embedding <=> %s::vector) AS similarity,
                   metadata
            FROM document_embeddings
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """
            cur.execute(sql, (query_vector, query_vector, limit))
            rows = cur.fetchall()
            for r in rows:
                sim = float(r[3])
                if sim >= threshold:
                    meta = r[4] or {}
                    chunks.append(
                        RetrievedChunk(
                            content=r[0],
                            source_file=r[1],
                            chunk_index=r[2],
                            similarity=round(sim, 4),
                            section=meta.get("section"),
                        )
                    )
        else:
            # Fallback: compute cosine dot product
            sql = "SELECT content, source_file, chunk_index, embedding, metadata FROM document_embeddings;"
            cur.execute(sql)
            rows = cur.fetchall()

            scored = []
            for r in rows:
                doc_vec = r[3]
                sim = dot_product(query_vector, doc_vec)
                meta = r[4] or {}
                if sim >= threshold:
                    scored.append((
                        sim,
                        RetrievedChunk(
                            content=r[0],
                            source_file=r[1],
                            chunk_index=r[2],
                            similarity=round(sim, 4),
                            section=meta.get("section"),
                        ),
                    ))

            # Sort descending by similarity
            scored.sort(key=lambda x: x[0], reverse=True)
            chunks = [item[1] for item in scored[:limit]]

        cur.close()
        conn.close()

        logger.info(
            "Retrieved %d chunks for query '%s' (threshold=%.2f, limit=%d)",
            len(chunks),
            query[:60],
            threshold,
            limit,
        )
        return chunks
