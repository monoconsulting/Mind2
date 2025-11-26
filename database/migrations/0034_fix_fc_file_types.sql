-- Migration 0032: Fix file_type values for FirstCard credit card invoices
-- Date: 2025-10-14
-- Purpose: Update legacy 'invoice' and 'invoice_page' types to 'cc_pdf' and 'cc_image'
--          for files uploaded via Kortmatchning (invoice_upload)

-- Update parent PDF files from 'invoice' to 'cc_pdf'
UPDATE unified_files
SET file_type = 'cc_pdf'
WHERE file_type = 'invoice'
  AND submitted_by = 'invoice_upload'
  AND original_filename LIKE 'FC_%';

-- Update page images from 'invoice_page' to 'cc_image'
UPDATE unified_files
SET file_type = 'cc_image'
WHERE file_type = 'invoice_page'
  AND submitted_by = 'invoice_upload'
  AND original_filename LIKE 'FC_%';

-- Also fix any PNG files that may have been incorrectly set
UPDATE unified_files
SET file_type = 'cc_image'
WHERE original_filename LIKE '%.png'
  AND submitted_by = 'invoice_upload'
  AND original_filename LIKE 'FC_%';

-- Show results
SELECT
  id,
  original_filename,
  file_type,
  submitted_by,
  created_at
FROM unified_files
WHERE submitted_by = 'invoice_upload'
ORDER BY created_at DESC;

