-- Complete test query for fetching all file information
-- This demonstrates how all the new database features work together

SELECT
    '=============================================' AS separator;
SELECT
    'COMPLETE FILE INFORMATION TEST RESULTS' AS title;
SELECT
    '=============================================' AS separator;

-- Get complete file information with all relationships
SELECT
    CONCAT('\nFile ID: ', uf.id) AS info,
    CONCAT('Type: ', uf.file_type) AS file_type,
    CONCAT('Original filename: ', IFNULL(uf.original_filename, 'N/A')) AS filename,
    CONCAT('File extension: ', IFNULL(uf.file_suffix, 'N/A')) AS extension,
    CONCAT('Category: ', IFNULL(fc.name, 'N/A'), ' (', IFNULL(fc.description, 'N/A'), ')') AS category,
    CONCAT('Created: ', uf.created_at) AS created,
    CONCAT('\n--- Merchant Info ---') AS merchant_header,
    CONCAT('Name: ', IFNULL(uf.merchant_name, 'N/A')) AS merchant,
    CONCAT('Org Nr: ', IFNULL(uf.orgnr, 'N/A')) AS org_nr,
    CONCAT('Purchase Date: ', IFNULL(uf.purchase_datetime, 'N/A')) AS purchase_date,
    CONCAT('Gross Amount: ', IFNULL(uf.gross_amount, 0)) AS gross,
    CONCAT('Net Amount: ', IFNULL(uf.net_amount, 0)) AS net
FROM unified_files uf
LEFT JOIN file_categories fc ON uf.file_category = fc.id
WHERE uf.id = 'test-file-001'
UNION ALL
SELECT
    CONCAT('\n--- Location Data ---') AS info,
    CONCAT('Latitude: ', fl.lat) AS lat,
    CONCAT('Longitude: ', fl.lon) AS lon,
    CONCAT('Accuracy: ', fl.acc, ' meters') AS accuracy,
    NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
FROM file_locations fl
WHERE fl.file_id = 'test-file-001'
UNION ALL
SELECT
    CONCAT('\n--- Tags (', COUNT(*), ' total) ---') AS info,
    GROUP_CONCAT(ft.tag ORDER BY ft.tag SEPARATOR ', ') AS tags,
    NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
FROM file_tags ft
WHERE ft.file_id = 'test-file-001'
GROUP BY ft.file_id;

-- Summary of all files in database
SELECT
    '\n=============================================' AS separator;
SELECT
    'SUMMARY OF ALL FILES IN DATABASE' AS title;
SELECT
    '=============================================' AS separator;

SELECT
    COUNT(*) as total_files,
    COUNT(DISTINCT file_category) as unique_categories,
    COUNT(DISTINCT file_suffix) as unique_extensions
FROM unified_files;

-- Files with complete metadata
SELECT
    '\n--- Files with Complete Metadata ---' AS header;

SELECT
    uf.id,
    uf.original_filename,
    uf.file_suffix,
    fc.name as category,
    CASE
        WHEN fl.file_id IS NOT NULL THEN 'Yes'
        ELSE 'No'
    END as has_location,
    CASE
        WHEN ft.file_id IS NOT NULL THEN 'Yes'
        ELSE 'No'
    END as has_tags,
    uf.merchant_name
FROM unified_files uf
LEFT JOIN file_categories fc ON uf.file_category = fc.id
LEFT JOIN file_locations fl ON uf.id = fl.file_id
LEFT JOIN (
    SELECT DISTINCT file_id FROM file_tags
) ft ON uf.id = ft.file_id
WHERE uf.file_type = 'receipt'
LIMIT 10;