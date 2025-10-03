-- Update AI system prompt titles to follow AI1-AI5 naming convention
-- Migration created: 2025-10-02

UPDATE ai_system_prompts
SET title = 'AI1: Document Classification',
    updated_at = NOW()
WHERE prompt_key = 'document_analysis';

UPDATE ai_system_prompts
SET title = 'AI2: Expense Classification',
    updated_at = NOW()
WHERE prompt_key = 'expense_classification';

UPDATE ai_system_prompts
SET title = 'AI3: Data Extraction',
    updated_at = NOW()
WHERE prompt_key = 'data_extraction';

UPDATE ai_system_prompts
SET title = 'AI4: Accounting Proposals',
    updated_at = NOW()
WHERE prompt_key = 'accounting_classification';

UPDATE ai_system_prompts
SET title = 'AI5: Credit Card Matching',
    updated_at = NOW()
WHERE prompt_key = 'credit_card_matching';
