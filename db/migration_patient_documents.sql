-- ============================================================
-- Project Baymax — Patient Documents Migration
-- Run in: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- 1. Create document_type enum
DO $$ BEGIN
    CREATE TYPE document_type AS ENUM ('report', 'xray', 'blood_test', 'prescription');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- 2. Patient documents table (typed, vector-searchable medical files)
--    NVIDIA nv-embedqa-e5-v5 produces 1024-dimensional embeddings
CREATE TABLE IF NOT EXISTS patient_documents (
    id               uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    patient_id       text NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    document_type    document_type NOT NULL,
    content_text     text NOT NULL,
    embedding        vector(1024),
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_patient_documents_patient_id
    ON patient_documents(patient_id);

CREATE INDEX IF NOT EXISTS idx_patient_documents_type
    ON patient_documents(patient_id, document_type);

-- 4. HNSW index for fast ANN cosine-distance search
CREATE INDEX IF NOT EXISTS idx_patient_documents_embedding_hnsw
    ON patient_documents
    USING hnsw (embedding vector_cosine_ops);

-- 5. Enable RLS (required for Supabase public schema security)
ALTER TABLE patient_documents ENABLE ROW LEVEL SECURITY;
