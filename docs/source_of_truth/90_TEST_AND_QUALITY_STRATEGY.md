# docs/source_of_truth/90_TEST_AND_QUALITY_STRATEGY.md

# Mind – Test and Quality Strategy (Source of Truth)

> This file describes how we ensure that Mind remains reliable as it evolves.

## 1. Test Types

Mind should use a combination of:

- **Unit tests** – For isolated business logic.
- **Integration tests** – For API endpoints, database interactions and pipelines.
- **End-to-end (E2E) tests** – For full flows (e.g. with Playwright for the web UI).
- **Data validation checks** – Ensuring schema and status invariants.

## 2. Minimum Requirements Before Release

- Critical paths covered:
  - Import → OCR → AI → Review path for receipts.
  - Import and processing of card statements.
  - Matching flow.
  - Export creation.

- No open P0 defects.

## 3. Special Focus Areas

- **Status consistency** – All status fields must follow `30_STATUS_MODEL.md`.
- **Data model stability** – Migrations must be tested on realistic data.
- **AI behavior** – Prompts and models must be stable enough for production use.

## 4. Tooling

- Existing tests (e.g. in `tests/` and Playwright suites) should be referenced here with:
  - How to run them.
  - Expected runtime.
  - How to interpret failures.

## 5. Governance

- New features must include appropriate tests.
- When changing core flows (status, pipelines, data model), ensure that SoT docs are updated and tests reflect the new truth.

---

