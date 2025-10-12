-- Add a column to store the file content hash.
-- It is nullable because existing records won't have a hash.
ALTER TABLE unified_files
ADD COLUMN content_hash VARCHAR(64) NULL DEFAULT NULL AFTER original_file_size;

-- Add a unique index to the new column.
-- In MySQL/InnoDB, a unique index allows multiple NULL values.
-- This prevents new duplicate files from being inserted while ignoring old records where the hash is NULL.
CREATE UNIQUE INDEX idx_content_hash ON unified_files(content_hash);
