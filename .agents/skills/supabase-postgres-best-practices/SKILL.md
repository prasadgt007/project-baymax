---
name: supabase-postgres-best-practices
description: Postgres performance optimization and best practices from Supabase. Use this skill when writing, reviewing, or optimizing Postgres queries, schema designs, or database configurations.
license: MIT
metadata:
  author: supabase
  version: "1.1.1"
  organization: Supabase
  date: January 2026
  source: https://github.com/supabase/agent-skills
---

# Supabase Postgres Best Practices

Comprehensive performance optimization guide for Postgres, maintained by Supabase. Contains rules across 8 categories, prioritized by impact to guide automated query optimization and schema design.

## When to Apply

Reference these guidelines when:
- Writing SQL queries
- Designing schemas
- Debugging slow queries
- Reviewing database code

## Category 1 — Query Performance (Critical)

### Use indexes for frequently filtered columns

```sql
-- Bad: no index on foreign key
CREATE TABLE patient_interactions (
    id uuid PRIMARY KEY,
    patient_id text  -- no index
);

-- Good: add index
CREATE INDEX idx_patient_interactions_patient_id
    ON patient_interactions(patient_id);
```

### Use pgvector indexes for vector similarity search

```sql
-- For ANN (Approximate Nearest Neighbor) at scale — use HNSW index
CREATE INDEX ON patient_interactions
    USING hnsw (embedding vector_cosine_ops);

-- Or IVFFlat for memory-constrained environments
-- CREATE INDEX ON patient_interactions
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### Avoid SELECT * in production queries

```sql
-- Bad
SELECT * FROM patients;

-- Good
SELECT patient_id, name, age FROM patients;
```

## Category 2 — Connection Management (Critical)

### Use connection pooling

- Always connect to port `6543` (Transaction pooler) for scripts and serverless functions
- Use port `5432` (Session pooler) only when you need prepared statements or advisory locks
- Never use the direct connection string (port `5432` on the direct host) from transient processes

### Keep connections short

```python
# Good: use context manager
with psycopg.connect(db_uri) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
```

## Category 3 — Schema Design

### Use UUIDs for primary keys

```sql
CREATE TABLE patient_interactions (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    ...
);
```

### Enable RLS on all public tables

```sql
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_interactions ENABLE ROW LEVEL SECURITY;
```

### Use text arrays for list fields instead of junction tables (when appropriate)

```sql
-- Simple list that doesn't need querying by individual elements
past_conditions text[] DEFAULT '{}'::text[]
```

## Category 4 — pgvector Best Practices

### Choose the right distance operator

| Operator | Distance Type | Use When |
|----------|--------------|----------|
| `<->` | L2 (Euclidean) | Raw embedding distances |
| `<=>` | Cosine | Normalized embeddings (recommended for NLP) |
| `<#>` | Inner product | Dot product similarity |

### Dimension must match your embedding model

```sql
-- NVIDIA nv-embedqa-e5-v5: 1024 dimensions
embedding vector(1024)
```

### Store NULL for rows without embeddings

```sql
-- Allow NULL for interactions not yet embedded
embedding vector(1024)  -- nullable by default
```
