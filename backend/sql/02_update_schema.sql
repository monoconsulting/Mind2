-- Check if columns exist before adding them
ALTER TABLE unified_files
ADD COLUMN file_category INT DEFAULT NULL COMMENT 'Reference to file_categories.id';

ALTER TABLE unified_files
ADD COLUMN file_suffix VARCHAR(32) DEFAULT NULL COMMENT 'File extension without dot';

-- Add foreign key constraint for file_category
ALTER TABLE unified_files
ADD CONSTRAINT fk_unified_files_category
FOREIGN KEY (file_category) REFERENCES file_categories(id)
ON DELETE SET NULL;

-- Add indexes for better query performance
CREATE INDEX idx_unified_files_category ON unified_files(file_category);
CREATE INDEX idx_unified_files_suffix ON unified_files(file_suffix);

-- Verify schema update
DESCRIBE unified_files;