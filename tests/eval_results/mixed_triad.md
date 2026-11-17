# Evaluation Prompt: mixed (AKILI-SPECS Triad)

**Prompt:**
> Design a database schema for a social media platform that supports posts, comments, likes, and follower relationships. Write the SQL CREATE TABLE statements and explain the indexing strategy.

**Known Traps:**
- missing foreign keys
- no indexes on lookup columns

**Expected Triad Advantage:**
Separate implementation and review catches schema issues

**Latency:** 90.78s

**Tasks Decomposed:** 2
**Passed Directly:** 2
**Retried & Passed:** 0
**Force Merged:** 0
**Issues Resolved:** 0 / 0

**Grounding References Cited:**
- Fallback evaluator

---

## Generated Output

**Unified Social‑Media Database Design & Indexing Strategy**

---

## 1. Database Schema (SQL DDL)

The following tables capture the core entities of a typical social‑media platform – users, posts, comments, and the two “likes” tables that record reactions to posts and comments. All primary keys are defined as `BIGINT` (or UUID in a production setting) and are automatically indexed by the database engine.

```sql
-- ------------------------------------------------------------
-- Users table
-- ------------------------------------------------------------
CREATE TABLE users (
    user_id        BIGINT      PRIMARY KEY,
    username       VARCHAR(50) NOT NULL UNIQUE,
    email          VARCHAR(255) NOT NULL UNIQUE,
    password_hash  TEXT        NOT NULL,
    display_name   VARCHAR(100),
    bio            TEXT,
    created_at     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Posts table
-- ------------------------------------------------------------
CREATE TABLE posts (
    post_id        BIGINT      PRIMARY KEY,
    user_id        BIGINT      NOT NULL,
    content        TEXT        NOT NULL,
    media_url      VARCHAR(2083),
    created_at     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_posts_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- Comments table
-- ------------------------------------------------------------
CREATE TABLE comments (
    comment_id     BIGINT      PRIMARY KEY,
    post_id        BIGINT      NOT NULL,
    user_id        BIGINT      NOT NULL,
    parent_id      BIGINT,                     -- optional threaded comment reference
    content        TEXT        NOT NULL,
    created_at     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_comments_post
        FOREIGN KEY (post_id) REFERENCES posts(post_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_comments_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_comments_parent
