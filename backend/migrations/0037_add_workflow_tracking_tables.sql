-- Migration 0037: Add workflow tracking infrastructure
-- Date: 2025-10-15
-- Purpose: Implement workflow isolation to prevent cross-contamination between receipt and credit card invoice workflows
--
-- This migration creates:
-- 1. workflow_runs table - tracks each workflow execution instance
-- 2. workflow_stage_runs table - tracks each stage within a workflow run
-- 3. Optional mirror fields on unified_files for workflow tracking
-- 4. Read-only views for observability and debugging

-- ========================================
-- 1. Create workflow_runs table
-- ========================================
CREATE TABLE IF NOT EXISTS workflow_runs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  workflow_key VARCHAR(40) NOT NULL COMMENT 'Workflow identifier: WF1_RECEIPT, WF2_CREDITCARD_INVOICE, WF2_PDF_SPLIT',
  source_channel VARCHAR(40) NULL COMMENT 'Source of file: web_upload, ftp, api, invoice_upload',
  file_id VARCHAR(36) NULL COMMENT 'FK to unified_files.id (root file that triggered this workflow)',
  content_hash VARCHAR(64) NULL COMMENT 'Content hash from unified_files for idempotence checks',
  current_stage VARCHAR(40) NOT NULL DEFAULT 'queued' COMMENT 'Current processing stage',
  status ENUM('queued','running','succeeded','failed','canceled') NOT NULL DEFAULT 'queued' COMMENT 'Overall workflow status',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  KEY idx_wfr_workflow (workflow_key),
  KEY idx_wfr_file (file_id),
  KEY idx_wfr_hash (content_hash),
  KEY idx_wfr_status (status),
  KEY idx_wfr_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Tracks workflow execution instances for hard workflow separation';

-- ========================================
-- 2. Create workflow_stage_runs table
-- ========================================
CREATE TABLE IF NOT EXISTS workflow_stage_runs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  workflow_run_id BIGINT NOT NULL COMMENT 'FK to workflow_runs.id',
  stage_key VARCHAR(40) NOT NULL COMMENT 'Stage identifier: pdf_to_png, ocr, ai1, ai2, ai3, ai4, ai6, merge_ocr, matching, etc.',
  status ENUM('queued','running','succeeded','failed','skipped') NOT NULL DEFAULT 'queued' COMMENT 'Stage execution status',
  started_at TIMESTAMP NULL COMMENT 'When stage execution began',
  finished_at TIMESTAMP NULL COMMENT 'When stage execution completed',
  message TEXT NULL COMMENT 'Short message with key metrics, error details, or progress info (max 200 chars recommended)',

  INDEX idx_wfs_workflow_run (workflow_run_id),
  INDEX idx_wfs_status (status),
  INDEX idx_wfs_stage (stage_key),

  CONSTRAINT fk_wfs_wfr FOREIGN KEY (workflow_run_id)
    REFERENCES workflow_runs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Tracks individual stage executions within workflow runs for observability';

-- ========================================
-- 3. Add optional mirror fields to unified_files
-- ========================================
-- These fields help track which workflow processed each file without requiring JOINs

-- Check if columns already exist before adding
SET @col_exists_workflow = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'unified_files'
    AND COLUMN_NAME = 'ingest_workflow_key'
);

SET @col_exists_channel = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'unified_files'
    AND COLUMN_NAME = 'ingest_source_channel'
);

-- Add ingest_workflow_key if it doesn't exist
SET @sql_workflow = IF(
  @col_exists_workflow = 0,
  'ALTER TABLE unified_files ADD COLUMN ingest_workflow_key VARCHAR(40) NULL COMMENT ''Workflow that processed this file: WF1_RECEIPT, WF2_CREDITCARD_INVOICE, etc.'' AFTER workflow_type',
  'SELECT ''Column ingest_workflow_key already exists'' AS Info'
);
PREPARE stmt_workflow FROM @sql_workflow;
EXECUTE stmt_workflow;
DEALLOCATE PREPARE stmt_workflow;

-- Add ingest_source_channel if it doesn't exist
SET @sql_channel = IF(
  @col_exists_channel = 0,
  'ALTER TABLE unified_files ADD COLUMN ingest_source_channel VARCHAR(40) NULL COMMENT ''Source channel: web_upload, ftp, api, invoice_upload'' AFTER ingest_workflow_key',
  'SELECT ''Column ingest_source_channel already exists'' AS Info'
);
PREPARE stmt_channel FROM @sql_channel;
EXECUTE stmt_channel;
DEALLOCATE PREPARE stmt_channel;

-- Add indexes for the new columns if they were created
SET @idx_exists_workflow = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'unified_files'
    AND INDEX_NAME = 'idx_ingest_workflow'
);

SET @sql_idx_workflow = IF(
  @idx_exists_workflow = 0 AND @col_exists_workflow = 0,
  'CREATE INDEX idx_ingest_workflow ON unified_files(ingest_workflow_key)',
  'SELECT ''Index idx_ingest_workflow already exists or column not created'' AS Info'
);
PREPARE stmt_idx_workflow FROM @sql_idx_workflow;
EXECUTE stmt_idx_workflow;
DEALLOCATE PREPARE stmt_idx_workflow;

-- ========================================
-- 4. Create helpful read-only views
-- ========================================

-- View: v_workflow_overview
-- Purpose: Quick overview of workflow runs with file information
CREATE OR REPLACE VIEW v_workflow_overview AS
SELECT
  wfr.id AS workflow_run_id,
  wfr.workflow_key,
  wfr.source_channel,
  wfr.file_id,
  wfr.content_hash,
  wfr.current_stage,
  wfr.status,
  wfr.created_at,
  wfr.updated_at,
  uf.original_filename,
  uf.mime_type,
  uf.file_suffix,
  uf.file_type,
  uf.workflow_type,
  uf.ai_status,
  uf.submitted_by
FROM workflow_runs wfr
LEFT JOIN unified_files uf ON uf.id = wfr.file_id
ORDER BY wfr.id DESC;

-- View: v_workflow_stages
-- Purpose: Detailed view of all workflow stages with timing and status
CREATE OR REPLACE VIEW v_workflow_stages AS
SELECT
  wfr.id AS workflow_run_id,
  wfr.workflow_key,
  wfr.file_id,
  wfr.status AS workflow_status,
  wfs.id AS stage_run_id,
  wfs.stage_key,
  wfs.status AS stage_status,
  wfs.started_at,
  wfs.finished_at,
  TIMESTAMPDIFF(SECOND, wfs.started_at, wfs.finished_at) AS duration_seconds,
  LEFT(wfs.message, 200) AS message_snippet,
  wfr.created_at AS workflow_created_at
FROM workflow_stage_runs wfs
JOIN workflow_runs wfr ON wfr.id = wfs.workflow_run_id
ORDER BY wfr.id DESC, wfs.id ASC;

-- ========================================
-- 5. Optional: Add unique constraint for idempotence
-- ========================================
-- Uncomment to prevent duplicate workflow runs for the same workflow+content_hash
-- This enforces "one workflow run per unique file content per workflow type"
--
-- ALTER TABLE workflow_runs
--   ADD UNIQUE KEY uniq_wfkey_contenthash (workflow_key, content_hash);

-- ========================================
-- Verification queries (for manual testing)
-- ========================================

-- Show table structure
-- SHOW CREATE TABLE workflow_runs;
-- SHOW CREATE TABLE workflow_stage_runs;

-- Show view definitions
-- SHOW CREATE VIEW v_workflow_overview;
-- SHOW CREATE VIEW v_workflow_stages;

-- Show columns added to unified_files
-- SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT
-- FROM INFORMATION_SCHEMA.COLUMNS
-- WHERE TABLE_SCHEMA = DATABASE()
--   AND TABLE_NAME = 'unified_files'
--   AND COLUMN_NAME IN ('ingest_workflow_key', 'ingest_source_channel');
