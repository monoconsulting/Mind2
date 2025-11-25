# Instructions and rules for agents
```
Version: 1.0.
Date: 2025-09-25
```

## Rules

* Mock data in the system are **not allowed.** This can not be used without a specific order to implement it
* **SQLLite can never be used.** You have no permissions to use this. 
* Test **must** be performed exactly as stated in `docs/SYSTEM_DOCS/TEST_RULES.md`
* You **must** follow the instructions in `GEMINI.md` for Gemini-specific guidelines.
* You **must** follow the workflow in `docs/TASK_MASTER_AGENT_INSTRUCTIONS.md` for all task management.
* Systemprompter: Agents **must never add or create new system prompts**. Only the approved, existing systemprompter entries may be used.
* For frontend tasks, refer to `docs/SYSTEM_DOCS/MIND_TASK_IMPLEMENTATION_REVIEW.md`.
* You are **never allowed to change port** or assign a new port to something that is not working.  You MUST ask permission
* You have **NO PERMISSIONS to use taskkill** to kill a port that someone else is using. This can cause serious damage
* You **ARE NOT ALLOWED TO EDIT playwright.config.ts**

## Documentation Structure

AI agents **must** store their generated reports in the following structure:

```
docs/agent-reports/
├── analysis/           # Codebase analysis reports
├── refactoring/        # Implementation plans & walkthroughs
├── reviews/            # Code review reports
└── archive/            # Older reports (6+ months)
```

**Naming convention:** Use date-prefixed descriptive names
- Example: `2025-11-21_codebase_analysis.md`
- Example: `2025-11-21_ai_service_refactoring_walkthrough.md`

**Report types:**
- **analysis/** - Codebase analysis reports, technical assessments
- **refactoring/** - Implementation plans, refactoring walkthroughs, design documents
- **reviews/** - Code review reports, verification results, test reports
- **archive/** - Reports older than 6 months (move periodically to keep main folders clean)
