-- 0045_add_prompt_and_response_to_ai_processing_history.sql
-- Purpose: Store full AI prompt and raw response separately (improves UI readability and prompt calibration).
-- Notes:
-- - LONGTEXT is used because prompts/responses can exceed TEXT (64KB).
-- - Existing log_text remains as a short human-readable summary (no prompts embedded).

ALTER TABLE ai_processing_history
  ADD COLUMN prompt_text LONGTEXT NULL COMMENT 'Full prompt text used for this AI call (snapshot)';

ALTER TABLE ai_processing_history
  ADD COLUMN response_text LONGTEXT NULL COMMENT 'Full raw AI response text returned by provider (snapshot)';
