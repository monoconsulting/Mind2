-- Migration: 0043_expand_prompt_content_to_mediumtext.sql
-- Date: 2025-12-09
-- Description: Expand prompt_content column from TEXT to MEDIUMTEXT to support longer AI prompts
-- TEXT max: 65,535 bytes (~64 KB)
-- MEDIUMTEXT max: 16,777,215 bytes (~16 MB)

ALTER TABLE ai_system_prompts
MODIFY COLUMN prompt_content MEDIUMTEXT;
