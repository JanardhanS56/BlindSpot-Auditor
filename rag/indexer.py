import asyncio
import logging
from pathlib import Path
import sys
import psycopg2
from psycopg2.extras import Json
import config
from rag.chunker import chunk_markdown
from rag.embedder import NvidiaEmbedder
from rag.setup_db import get_connection, setup_database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("rag.indexer")


class KnowledgeBaseIndexer:
    """Indexes markdown knowledge base documents into PostgreSQL vector storage."""

    def __init__(
        self,
        embedder: NvidiaEmbedder | None = None,
        kb_dir: Path | str | None = None,
    ):
        self.embedder = embedder or NvidiaEmbedder()
        self.kb_dir = Path(kb_dir or (Path(__file__).resolve().parent.parent / "knowledge_base"))
        self._has_vector_ext: bool | None = None

    def _ensure_table(self):
        """Ensures the document_embeddings table exists and detects vector extension."""
        if self._has_vector_ext is None:
            self._has_vector_ext = setup_database()

    async def index_file(self, filepath: str | Path) -> int:
        """Chunks, embeds, and indexes a single markdown file."""
        self._ensure_table()
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Knowledge base file does not exist: {path}")

        chunks = chunk_markdown(str(path))
        if not chunks:
            logger.info("No chunks produced from %s", path.name)
            return 0

        logger.info("Parsed %d chunks from %s. Embedding...", len(chunks), path.name)
        texts = [c["content"] for c in chunks]
        embeddings = await self.embedder.embed_batch(texts, input_type="passage")

        conn = get_connection()
        conn.autocommit = True
        cur = conn.cursor()

        indexed_count = 0
        for chunk, emb in zip(chunks, embeddings):
            metadata = {
                "section": chunk["section"],
                "source": chunk["source"],
            }
            if self._has_vector_ext:
                query = """
                INSERT INTO document_embeddings (source_file, chunk_index, content, embedding, metadata)
                VALUES (%s, %s, %s, %s::vector, %s)
                ON CONFLICT (source_file, chunk_index) DO UPDATE
                SET content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata;
                """
            else:
                query = """
                INSERT INTO document_embeddings (source_file, chunk_index, content, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (source_file, chunk_index) DO UPDATE
                SET content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata;
                """

            cur.execute(
                query,
                (
                    chunk["source"],
                    chunk["chunk_index"],
                    chunk["content"],
                    emb,
                    Json(metadata),
                ),
            )
            indexed_count += 1

        cur.close()
        conn.close()
        logger.info("Successfully indexed %d chunks for %s", indexed_count, path.name)
        return indexed_count

    async def index_all(self) -> int:
        """Indexes all markdown documents in the knowledge base directory."""
        self._ensure_table()
        if not self.kb_dir.exists():
            raise FileNotFoundError(f"Knowledge base directory not found: {self.kb_dir}")

        md_files = [f for f in self.kb_dir.glob("*.md") if f.name != "README.md"]
        logger.info("Found %d markdown knowledge base documents in %s", len(md_files), self.kb_dir)

        total_indexed = 0
        for md_file in md_files:
            count = await self.index_file(md_file)
            total_indexed += count

        logger.info("Full indexing complete. Total chunks indexed: %d", total_indexed)
        return total_indexed


async def main():
    indexer = KnowledgeBaseIndexer()
    await indexer.index_all()


if __name__ == "__main__":
    asyncio.run(main())
