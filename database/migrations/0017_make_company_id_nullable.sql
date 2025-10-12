-- Allow the company_id in unified_files to be NULL.
-- This is necessary because the company is unknown at the time of initial file ingestion.
-- The AI pipeline is responsible for populating this value later.
ALTER TABLE unified_files MODIFY COLUMN company_id INT NULL;
