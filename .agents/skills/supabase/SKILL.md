---
name: supabase
description: "Use when doing ANY task involving Supabase. Triggers: Supabase products (Database, Auth, Edge Functions, Realtime, Storage, Vectors, Cron, Queues); client libraries and SSR integrations (supabase-js, @supabase/ssr) in Next.js, React, SvelteKit, Astro, Remix; auth issues (login, logout, sessions, JWT, cookies, getSession, getUser, getClaims, RLS); Supabase CLI or MCP server; schema changes, migrations, security audits, Postgres extensions (pg_graphql, pg_cron, pg_vector)."
metadata:
  author: supabase
  version: "0.1.2"
  source: https://github.com/supabase/agent-skills
---

# Supabase

## Core Principles

**1. Supabase changes frequently — verify against changelog and current docs before implementing.**
Do not rely on training data for Supabase features. Function signatures, config.toml settings, and API conventions change between versions.

First, fetch `https://supabase.com/changelog.md` (a lightweight summary index — not a heavy pull), scan for `breaking-change` tags relevant to your task, and follow the linked page for any that apply. Then look up the relevant topic using the documentation access methods below.

**2. Verify your work.**
After implementing any fix, run a test query to confirm the change works. A fix without verification is incomplete.

**3. Recover from errors, don't loop.**
If an approach fails after 2-3 attempts, stop and reconsider. Try a different method, check documentation, inspect the error more carefully, and review relevant logs when available.

**4. Exposing tables to the Data API.**
Newly created tables may not be automatically exposed via the Data (REST) API. `anon` and `authenticated` roles may need to be explicitly granted access.

> Note: This is separate from RLS, which controls which _rows_ are visible once a table is accessible.

**5. RLS in exposed schemas.**
Enable RLS on every table in any exposed schema (including `public` by default). After enabling RLS, create policies that match the actual access model.

**6. Security checklist.**
When working on any Supabase task that touches auth, RLS, views, storage, or user data:

- **Auth and session security**
  - **Never use `user_metadata` claims in JWT-based authorization decisions.** `raw_user_meta_data` is user-editable. Store authorization data in `raw_app_meta_data` / `app_metadata` instead.
  - **Deleting a user does not invalidate existing access tokens.** Sign out or revoke sessions first.
  - **JWT claims are not always fresh until the user's token is refreshed.**

- **API key and client exposure**
  - **Never expose the `service_role` or secret key in public clients.** Prefer publishable keys for frontend code.

- **RLS, views, and privileged database code**
  - **Views bypass RLS by default.** Use `CREATE VIEW ... WITH (security_invoker = true)` in Postgres 15+.
  - **UPDATE requires a SELECT policy.** An UPDATE needs to first SELECT the row.

## Python Backend with psycopg3 (Direct Connection)

For Python backend services connecting directly to Postgres (no Supabase JS client needed):

```python
import psycopg
import os

# Use the pooler URI from Supabase Dashboard > Settings > Database > Connection string > URI
# Port 6543 = Transaction pooler (recommended for serverless/scripts)
# Port 5432 = Session pooler (for persistent connections with prepared statements)
conn = psycopg.connect(os.environ["SUPABASE_DB_URI"])
```

## pgvector with Python

```python
from pgvector.psycopg import register_vector
import psycopg

conn = psycopg.connect(os.environ["SUPABASE_DB_URI"])
register_vector(conn)

# ANN search with cosine distance operator <=>
cur = conn.cursor()
cur.execute(
    "SELECT id, notes FROM patient_interactions ORDER BY embedding <=> %s LIMIT %s",
    (embedding_list, limit)
)
```
