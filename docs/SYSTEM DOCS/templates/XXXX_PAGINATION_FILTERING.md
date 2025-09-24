# Pagination, Filtering, Sorting, Sparse Fields

AI INSTRUCTIONS (DO NOT REMOVE)

**Template Notice:** This document is a template. You **must** replace all occurrences of `XXXX` with your project name and fill in the placeholders with actual values. Validate ports with Atlas first — see **@CHECK_PORTS_API.md**.**

Purpose: This document is editable by AI/humans. Follow these rules:

1) This is a TEMPLATE. Replace placeholders with project-specific values.
2) "XXXX_" prefix MUST be replaced with the actual PROJECT NAME (kebab_case or snake_case).
3) Ports MUST NOT be assigned until verified against the authoritative Atlas port list.
   See @CHECK_PORTS_API.md for the verification workflow.
4) Do NOT hardcode host ports or secrets in code or docs. Use env vars and .env(.example).
5) Never delete sections. If you deprecate something, strike it through and explain why.
6) Update the **CHANGELOG** table (versioning in 0.1 steps) whenever content changes.
7) Keep consistency across docs: PORTS, API bases, Endpoints, OpenAPI, Env vars, Security.
8) **The file must be saved in the following folder @docs\SYSTEMDOCS - with the correct name: PROJECT_NAME_DOCUMENTATION_NAME.md**. Example: MIND_ENDPOINTS_v.1.4.md
9) **Template Notice:** This document is a template. You **must** replace all occurrences of `XXXX` with your project name and fill in the placeholders with actual values. Validate ports with Atlas first — see **@CHECK_PORTS_API.md**.

------

## **Changelog**

| Date       | Filename                                 | Version | Changes                                          | Author                                                       |
| ---------- | ---------------------------------------- | ------- | ------------------------------------------------ | ------------------------------------------------------------ |
| YYYY-MM-DD | PROJECT_NAME_DOCUMENTATION_NAME_v.1.1.md | 1.1     | Write the changes that are made in the file here | If you are an agent write what agent you are (example - Gemini, Chat GPT 5) |
|            |                                          |         |                                                  |                                                              |
|            |                                          |         |                                                  |                                                              |

------



# XXXX — Pagination, Filtering, Sorting, Sparse Fields (Template)

- Pagination: **cursor-based**
  - Query: `limit` (1..200, default 50), `after` (opaque cursor)
  - Response: `"page": {"limit": n, "next": "<cursor-or-null>"}`
- Filtering:
  - `q` free text
  - Field filters: `status=in:active,pending`, `createdAt>=YYYY-MM-DD`
- Sorting: `sort=-createdAt,name`
- Sparse fieldsets: `fields=item:id,name,createdAt`


## Validation Checklist
- [ ] Replaced all `XXXX` with the actual project name
- [ ] Ports verified with Atlas (see @CHECK_PORTS_API.md)
- [ ] `.env.example` updated accordingly
- [ ] Cross-referenced with OPENAPI / ENDPOINTS / ENV_VARS
- [ ] Security review: no secrets; headers/policies intact
- [ ] Observability hooks documented (logs/metrics/traces)


## Changelog:  

| Version number | Date       | Changes made     |
| -------------- | ---------- | ---------------- |
| 0.9            | 2025-09-03 | Template version |

