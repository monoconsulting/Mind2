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

# XXXX —CHECK_PORTS_API

```
File: XXXX_CHECK_PORTS_API_v.0.0.md
Version: 0.0

```

## **Changelog**

| Date       | Filename                                 | Version | Changes                                          | Author                                                       |
| ---------- | ---------------------------------------- | ------- | ------------------------------------------------ | ------------------------------------------------------------ |
| YYYY-MM-DD | PROJECT_NAME_DOCUMENTATION_NAME_v.1.1.md | 1.1     | Write the changes that are made in the file here | If you are an agent write what agent you are (example - Gemini, Chat GPT 5) |
|            |                                          |         |                                                  |                                                              |
|            |                                          |         |                                                  |                                                              |



**Goal:** Ensure no port collisions across teams/stacks. This doc is the **only** place describing how to verify/allocate ports.

## Workflow
1. Search Atlas for existing allocations.
2. Propose new host ports for services (see `XXXX_PORTS.md`). **Do not assign yet.**
3. Submit a request/ticket in Atlas to reserve host ports:
   - Service name
   - Intended host port
   - Environment (dev/stage/prod)
   - Owner/contact
4. Once approved, update:
   - `.env.example` with new `*_PORT` values
   - `XXXX_PORTS.md` table
5. Run `ports_guard.py --strict` (if available) to validate mappings.
6. Rename files from `XXXX_*.md` to `<project>_*.md` and replace all `XXXX` placeholders.

## Evidence
- Paste Atlas reservation link or ID here:
  - Reservation: `ATLAS-<ID>`
  - Date/time (Europe/Stockholm, RFC3339)


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

