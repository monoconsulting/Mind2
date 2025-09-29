-- Add FTP metadata columns to unified_files table
-- These columns are referenced in FTP import services but missing from schema

ALTER TABLE unified_files
ADD COLUMN original_file_id VARCHAR(36) NULL COMMENT 'Original file ID from FTP source',
ADD COLUMN original_file_name VARCHAR(222) NULL COMMENT 'Original filename from FTP source',
ADD COLUMN file_creation_timestamp TIMESTAMP NULL COMMENT 'File creation timestamp from FTP metadata',
ADD COLUMN original_file_size INT NULL COMMENT 'Original file size in bytes',
ADD COLUMN mime_type VARCHAR(222) NULL COMMENT 'MIME type of the original file';

-- Add indexes for better query performance
CREATE INDEX idx_unified_files_creation_timestamp ON unified_files(file_creation_timestamp);
CREATE INDEX idx_unified_files_original_file_id ON unified_files(original_file_id);

-- Verify the changes
DESCRIBE unified_files;