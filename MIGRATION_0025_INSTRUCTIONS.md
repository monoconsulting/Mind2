# Migration 0025 - Update AI Prompt Titles

## Purpose
Updates AI system prompt titles to follow the standardized "AI1: Title" format and ensures they are sorted correctly in the UI.

## Changes Made

### Backend (ai_config.py)
- Updated SQL query to sort prompts by their logical AI number (AI1-AI5) instead of database ID
- Uses CASE statement to map prompt_key to sort order

### Database Migration (0025_update_ai_prompt_titles.sql)
Updates prompt titles to standardized format:
- AI1: Document Classification
- AI2: Expense Classification
- AI3: Data Extraction
- AI4: Accounting Proposals
- AI5: Credit Card Matching

## How to Run Migration

### Option 1: Using MySQL CLI
```bash
mysql -u root -p'uPBfGkgm9S2hHPYx' mono_se_db_9 < database/migrations/0025_update_ai_prompt_titles.sql
```

### Option 2: Using Python Script
```bash
python run_migration_0025.py
```

### Option 3: Manual SQL
Run each UPDATE statement from `database/migrations/0025_update_ai_prompt_titles.sql` manually in your MySQL client.

## Verification

After running the migration, verify in the AI menu that:
1. Prompts are displayed in order: AI1, AI2, AI3, AI4, AI5
2. Each prompt title follows the "AI#: Title" format
3. No prompts are missing or duplicated

## Related Files
- `backend/src/api/ai_config.py` - Backend API endpoint with new sorting logic
- `database/migrations/0025_update_ai_prompt_titles.sql` - Migration SQL
- `main-system/app-frontend/src/ui/pages/Ai.jsx` - Frontend component (no changes needed)
