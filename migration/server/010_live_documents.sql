BEGIN;

CREATE TABLE IF NOT EXISTS live_documents (
    collection text NOT NULL,
    doc_id text NOT NULL,
    data jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT NOW(),
    updated_at timestamptz NOT NULL DEFAULT NOW(),
    PRIMARY KEY (collection, doc_id)
);

CREATE INDEX IF NOT EXISTS live_documents_collection_updated_idx
    ON live_documents (collection, updated_at DESC);

CREATE INDEX IF NOT EXISTS live_documents_data_gin_idx
    ON live_documents USING gin (data);

INSERT INTO migration_log (migration_name, status)
SELECT '010_live_documents_compat', 'completed'
WHERE NOT EXISTS (
    SELECT 1 FROM migration_log
    WHERE migration_name='010_live_documents_compat'
);

COMMIT;
