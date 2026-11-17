# Evaluation Prompt: mixed (Single-Agent Baseline)

**Prompt:**
> Design a database schema for a social media platform that supports posts, comments, likes, and follower relationships. Write the SQL CREATE TABLE statements and explain the indexing strategy.

**Known Traps:**
- missing foreign keys
- no indexes on lookup columns

**Latency:** 11.99s

---

## Generated Output

Below is a **complete relational schema** that covers the core entities of a typical “Twitter‑/Instagram‑like” social network:

* **users** – the accounts that own everything else  
* **posts** – text (or media) that a user creates  
* **comments** – replies to a post (or to another comment – optional)  
* **likes** – a many‑to‑many relationship between users and posts (or comments)  
* **follows** – the follower / followee relationship between users  

The statements are written for **PostgreSQL** (they work in MySQL/InnoDB with only minor syntax tweaks – e.g. `SERIAL` → `BIGINT AUTO_INCREMENT`).  
All tables use **UTC timestamps** and **soft‑delete** (`deleted_at`) so that you can keep audit trails without physically removing rows.

---

## 1️⃣ CREATE TABLE statements

```sql
-----------------------------------------------------------------
-- 1. USERS
-----------------------------------------------------------------
CREATE TABLE users (
    user_id        BIGSERIAL PRIMARY KEY,
    username       VARCHAR(50)   NOT NULL UNIQUE,
    email          VARCHAR(255)  NOT NULL UNIQUE,
    password_hash  BYTEA         NOT NULL,
    display_name   VARCHAR(100),
    bio            TEXT,
    avatar_url     TEXT,
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    deleted_at     TIMESTAMPTZ   NULL
);

-----------------------------------------------------------------
-- 2. POSTS
-----------------------------------------------------------------
CREATE TABLE posts (
    post_id        BIGSERIAL PRIMARY KEY,
    author_id      BIGINT        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    content        TEXT          NOT NULL,
    media_url      TEXT,                     -- optional image/video
    is_public      BOOLEAN       NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    deleted_at     TIMESTAMPTZ   NULL
);

-----------------------------------------------------------------
-- 3. COMMENTS
-----------------------------------------------------------------
CREATE TABLE comments (
    comment_id     BIGSERIAL PRIMARY KEY,
    post_id        BIGINT        NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
    author_id      BIGINT        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    parent_id      BIGINT        NULL REFERENCES comments(comment_id) ON DELETE CASCADE,
    content        TEXT          NOT NULL,
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    deleted_at     TIMESTAMPTZ   NULL
);

-----------------------------------------------------------------
-- 4. LIKES (likes on posts – you can add a separate table for comment likes)
-----------------------------------------------------------------
CREATE TABLE likes (
    user_id        BIGINT        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    post_id        BIGINT        NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, post_id)               -- one like per user/post
);

-----------------------------------------------------------------
-- 5. FOLLOWS (directed follower relationship)
-----------------------------------------------------------------
CREATE TABLE follows (
    follower_id    BIGINT        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    followee_id    BIGINT        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (follower_id, followee_id),      -- prevents duplicate follows
    CHECK (follower_id <> followee_id)           -- you cannot follow yourself
);
```

### Optional extensions (not required for the core ask)

* `post_likes` for comment likes (`comment_id` instead of `post_id`).
* `post_tags`, `post_mentions`, `user_settings`, etc.

---

## 2️⃣ Indexing strategy

| Table      | Index(es) | Why it’s needed (typical queries) |
|------------|-----------|-----------------------------------|
| **users**  | PK (`user_id`) – automatically indexed. <br>Unique indexes on `username` and `email`. | Look‑ups by login credentials, profile pages, uniqueness enforcement. |
| **posts**  | PK (`post_id`). <br>**FK index** on `author_id`. <br>Composite index **`(author_id, created_at DESC)`**. <br>Composite index **`(is_public, created_at DESC)`** (optional). | • Fetch a user’s own posts (profile page). <br>• Build a home‑feed: recent public posts from people you follow → join `posts` → `follows`. <br>• Filter by visibility (`is_public`). |
| **comments** | PK (`comment_id`). <br>FK index on `post_id`. <br>FK index on `author_id`. <br>Composite index **`(post_id, created_at ASC)`**. | • Load all comments for a post ordered chronologically. <br>• Show a user’s recent comments. |
| **likes**  | PK (`user_id, post_id`) – also serves as a **unique index**. <br>Separate index on `post_id` (covers “how many likes a post has”). | • `SELECT COUNT(*) FROM likes WHERE post_id = ?` → fast because of index on `post_id`. <br>• Check if a user already liked a post (`WHERE user_id = ? AND post_id = ?`). |
| **follows**| PK (`follower_id, followee_id`). <br>Separate index on `followee_id` (to get a user’s followers). <br>Optional **`(follower_id, created_at DESC)`** for “who did I follow most recently”. | • Build a feed: `SELECT followee_id FROM follows WHERE follower_id = ?`. <br>• Show a user’s follower count (`WHERE followee_id = ?`). <br>• Suggest “people you may know” by
