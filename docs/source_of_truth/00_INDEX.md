# docs/source_of_truth/00_INDEX.md

# Mind – Source of Truth Index

> This directory contains the canonical, current documentation for the Mind system. Older or exploratory documents live under `docs/archive` or `docs/wip`.

## Purpose

This file is the navigation hub for all source-of-truth (SoT) documentation for the Mind project. If there is a conflict between code comments, legacy docs and these files, the files listed below are considered the authoritative source.

## Document List

- `10_SYSTEM_OVERVIEW.md` – High-level summary of Mind, key capabilities and core architecture.
- `20_DOMAIN_MODEL_AND_GLOSSARY.md` – Domain concepts (Company, Project, Receipt, Invoice, Card Transaction, etc.) and how they relate.
- `30_STATUS_MODEL.md` – All status fields and allowed values (processing, receipt, invoice, match, AI stages, etc.) including state diagrams.
- `40_DATA_MODEL.md` – Canonical description of the database schema and key relations.
- `50_PIPELINES_AND_JOBS.md` – All processing flows (FTP import, OCR, AI1–AI7, matching, export to accounting).
- `60_INTEGRATIONS.md` – External systems and services (OCR, AI, email/IMAP, FirstCard/credit card providers, accounting systems, etc.).
- `80_OPERATIONS_RUNBOOK.md` – How to operate, debug and maintain the system in daily work.
- `90_TEST_AND_QUALITY_STRATEGY.md` – Strategy for tests, validation and quality gates.

## Ownership

- **Documentation Owner:** _TBD (Mind system owner)_
- **Last Updated:** _TBD_

The Documentation Owner is responsible for ensuring that changes to architecture, data model, statuses and pipelines are reflected in these files before or together with production changes.

“Schema and status definitions in code/migrations **may not change** without updating `40_DATA_MODEL.md` and `30_STATUS_MODEL.md`.”