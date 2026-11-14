import logging
import sys
import psycopg2
from psycopg2.extras import Json
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("rag.setup_db")


def get_connection():
    """Establishes connection to PostgreSQL using settings from config."""
    return psycopg2.connect(
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        dbname=config.POSTGRES_MAINTAINANCE_DB,
        user=config.POSTGRES_USERNAME,
        password=config.POSTGRES_PASSWORD,
    )


def setup_database(dimension: int = 4096) -> bool:
    """Sets up the pgvector extension and document_embeddings table."""
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()

    has_vector_ext = False
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        has_vector_ext = True
        logger.info("Successfully enabled pgvector extension.")
    except Exception as e:
        logger.warning(
            "pgvector extension not installed in PostgreSQL system: %s. Using array fallback for vector storage.",
            e,
        )

    if has_vector_ext:
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS document_embeddings (
            id SERIAL PRIMARY KEY,
            source_file TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding vector({dimension}),
            metadata JSONB DEFAULT '{{}}',
            created_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_source_chunk UNIQUE (source_file, chunk_index)
        );
        """
        cur.execute(create_table_sql)
        try:
            cur.execute(
                "CREATE INDEX IF NOT EXISTS document_embeddings_ivfflat_idx "
                "ON document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);"
            )
            logger.info("IVFFlat cosine index created.")
        except Exception as idx_err:
            logger.warning("Could not create IVFFlat index (table may be empty): %s", idx_err)
    else:
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS document_embeddings (
            id SERIAL PRIMARY KEY,
            source_file TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding float8[],
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_source_chunk UNIQUE (source_file, chunk_index)
        );
        """
        cur.execute(create_table_sql)

    # Verification: test insert + select + delete
    logger.info("Verifying document_embeddings table with test insert...")
    dummy_vec = [0.0] * dimension
    test_file = "__test_verification__.md"
    
    cur.execute(
        "DELETE FROM document_embeddings WHERE source_file = %s;",
        (test_file,),
    )
    
    if has_vector_ext:
        cur.execute(
            """
            INSERT INTO document_embeddings (source_file, chunk_index, content, embedding, metadata)
            VALUES (%s, %s, %s, %s::vector, %s) RETURNING id;
            """,
            (test_file, 0, "Test verification content", dummy_vec, Json({"test": True})),
        )
    else:
        cur.execute(
            """
            INSERT INTO document_embeddings (source_file, chunk_index, content, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s) RETURNING id;
            """,
            (test_file, 0, "Test verification content", dummy_vec, Json({"test": True})),
        )

    test_id = cur.fetchone()[0]
    cur.execute("SELECT id, source_file, content FROM document_embeddings WHERE id = %s;", (test_id,))
    row = cur.fetchone()
    logger.info("Verification succeeded: row %s retrieved (%s).", row[0], row[1])

    # Clean up test row
    cur.execute("DELETE FROM document_embeddings WHERE id = %s;", (test_id,))
    logger.info("Test row cleaned up.")

    cur.close()
    conn.close()
    return has_vector_ext


if __name__ == "__main__":
    setup_database()
