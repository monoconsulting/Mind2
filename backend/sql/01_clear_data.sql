-- Clear all existing file data from all tables
SET FOREIGN_KEY_CHECKS = 0;

-- Clear file-related tables
TRUNCATE TABLE file_tags;
TRUNCATE TABLE file_locations;
TRUNCATE TABLE ai_processing_history;
TRUNCATE TABLE ai_processing_queue;
TRUNCATE TABLE ai_accounting_proposals;
TRUNCATE TABLE unified_files;

-- Clear invoice-related tables (they have foreign keys to unified_files)
TRUNCATE TABLE invoice_line_history;
TRUNCATE TABLE invoice_lines;
TRUNCATE TABLE invoice_documents;

SET FOREIGN_KEY_CHECKS = 1;

-- Verify tables are empty
SELECT 'unified_files' as table_name, COUNT(*) as record_count FROM unified_files
UNION ALL
SELECT 'file_tags', COUNT(*) FROM file_tags
UNION ALL
SELECT 'file_locations', COUNT(*) FROM file_locations
UNION ALL
SELECT 'ai_processing_history', COUNT(*) FROM ai_processing_history
UNION ALL
SELECT 'ai_processing_queue', COUNT(*) FROM ai_processing_queue;