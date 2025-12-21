-- Repair mojibake in seeded ai_system_prompts metadata (introduced by 0041_add_ai_llm_tables.sql)
-- This is intentionally narrowly-scoped and only updates rows that match the known bad bytes.

UPDATE ai_system_prompts
SET title = 'Utlägg eller företag'
WHERE prompt_key = 'expense_classification'
  AND HEX(title) = '55746cc383c2a4676720656c6c65722066c383c2b67265746167';

UPDATE ai_system_prompts
SET description = 'Avgör om ett kvitto är ett personligt utlägg eller företagskostnad'
WHERE prompt_key = 'expense_classification'
  AND HEX(description) = '417667c383c2b672206f6d20657474206b766974746f20c383c2a4722065747420706572736f6e6c6967742075746cc383c2a4676720656c6c65722066c383c2b67265746167736b6f73746e6164';

