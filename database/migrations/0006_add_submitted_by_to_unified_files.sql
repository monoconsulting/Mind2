-- Add submitted_by to unified_files for UI/user filtering
ALTER TABLE unified_files ADD COLUMN submitted_by VARCHAR(64) NULL;

