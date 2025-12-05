# docs/source_of_truth/00_INDEX.md

# Mind – Source of Truth Index

> This directory contains the canonical, current documentation for the Mind system. Older or exploratory documents live under `docs/archive` or `docs/wip`.

## Purpose

This file is the navigation hub for all source-of-truth (SoT) documentation for the Mind project. If there is a conflict between code comments, legacy docs and these files, the files listed below are considered the authoritative source.

## Document List

| File | Description | Status |
|------|-------------|--------|
| `10_SYSTEM_OVERVIEW.md` | High-level summary of Mind, key capabilities and core architecture | Complete |
| `20_DOMAIN_MODEL_AND_GLOSSARY.md` | Domain concepts (Company, Receipt, Invoice, Card Transaction, etc.) and how they relate | Complete |
| `30_STATUS_MODEL.md` | All status fields and allowed values (ai_status, workflow status, match status) including state diagrams | Complete |
| `40_DATA_MODEL.md` | Canonical description of the database schema and key relations | Complete |
| `50_PIPELINES_AND_JOBS.md` | All processing flows (WF1_RECEIPT, WF2_PDF_SPLIT, WF3_FIRSTCARD_INVOICE) | Complete |
| `55_API_AND_ENDPOINTS.md` | REST API endpoints, contracts, and authentication requirements | Complete |
| `60_INTEGRATIONS.md` | External systems and services (OCR, AI, FirstCard, accounting systems) | Complete |
| `70_AI_PROMPTS_AND_ROLES.md` | AI roles (AI1–AI6), prompts, input/output contracts | Complete |
| `80_OPERATIONS_RUNBOOK.md` | How to operate, debug and maintain the system in daily work | Complete |
| `90_TEST_AND_QUALITY_STRATEGY.md` | Strategy for tests, validation and quality gates | Complete |

## Supporting Files

- `agents.md` – Agent governance and system instructions (SYSTEM_GOVERNANCE + PROJECT_PLAN)
- `docs/wip/DOCUMENT_INVENTORY.md` – Complete inventory of all documentation
- `docs/wip/CONFLICTS_AND_DECISIONS.md` – Identified conflicts and resolution decisions

## Ownership

- **Documentation Owner:** Mind System Owner
- **Last Updated:** 2025-12-04
- **Consolidated By:** Agent 1 – Source of Truth Consolidator

The Documentation Owner is responsible for ensuring that changes to architecture, data model, statuses and pipelines are reflected in these files before or together with production changes.

“Schema and status definitions in code/migrations **may not change** without updating `40_DATA_MODEL.md` and `30_STATUS_MODEL.md`.”