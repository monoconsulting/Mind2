-- Add created_at to file_tags to align with ingest writes
ALTER TABLE file_tags ADD COLUMN created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP;

