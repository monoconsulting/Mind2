-- Make orgnr nullable in companies table
-- Companies may not always have organization numbers (e.g., international vendors)
ALTER TABLE companies MODIFY COLUMN orgnr VARCHAR(22) NULL;

-- Update unique constraint to handle NULL values properly
-- MySQL allows multiple NULL values in unique indexes
-- This ensures we can have multiple companies without orgnr
DROP INDEX IF EXISTS ux_companies_orgnr ON companies;
CREATE UNIQUE INDEX ux_companies_orgnr ON companies(orgnr);
