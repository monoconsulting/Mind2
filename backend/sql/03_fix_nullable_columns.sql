-- Fix NOT NULL columns that should allow NULL values
-- These fields might not always be available in metadata

ALTER TABLE unified_files
  MODIFY COLUMN original_file_id varchar(36) NULL,
  MODIFY COLUMN original_file_name varchar(222) NULL,
  MODIFY COLUMN file_creation_timestamp timestamp NULL,
  MODIFY COLUMN original_file_size int NULL,
  MODIFY COLUMN mime_type varchar(222) NULL;

-- Verify the changes
DESCRIBE unified_files;