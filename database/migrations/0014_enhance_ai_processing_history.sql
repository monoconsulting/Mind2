-- Enhance ai_processing_history table with detailed logging columns
-- This migration adds columns to track AI stage names, detailed logs, and error information

ALTER TABLE ai_processing_history
  ADD COLUMN ai_stage_name VARCHAR(64) NULL COMMENT 'Human-readable AI stage name (AI1-DocumentClassification, AI2-ExpenseClassification, etc.)';

ALTER TABLE ai_processing_history
  ADD COLUMN log_text TEXT NULL COMMENT 'Detailed log message explaining what happened in this stage';

ALTER TABLE ai_processing_history
  ADD COLUMN error_message TEXT NULL COMMENT 'Error message if the stage failed';

ALTER TABLE ai_processing_history
  ADD COLUMN confidence FLOAT NULL COMMENT 'Confidence score for this AI stage result';

ALTER TABLE ai_processing_history
  ADD COLUMN processing_time_ms INT NULL COMMENT 'Processing time in milliseconds';

ALTER TABLE ai_processing_history
  ADD COLUMN provider VARCHAR(64) NULL COMMENT 'AI provider used (rule-based, openai, azure, etc.)';

ALTER TABLE ai_processing_history
  ADD COLUMN model_name VARCHAR(128) NULL COMMENT 'Model name used for this stage';

-- Add indexes for better query performance
-- Note: These will error if they already exist, which is safe to ignore
CREATE INDEX idx_file_stage ON ai_processing_history(file_id, ai_stage_name);
CREATE INDEX idx_status ON ai_processing_history(status);