# Research — Mind system feature

Date: 2025-09-20
Branch: 001-mind-system-receipt

## Open Questions (NEEDS CLARIFICATION)
1) Authentication & roles: public submitter vs. authenticated users? admin role granularity? Owner: PO — Due: 2025-09-25
2) Data retention: how long to keep images/extracted data; deletion rights? Owner: Legal — Due: 2025-09-25
3) Location data consent scope and revocation path? Owner: PO/Legal — Due: 2025-09-25
4) Invoice/Other doc handling flows (queues, UI)? Owner: PO — Due: 2025-09-25
5) Duplicate criteria (date+amount+merchant?): confirm heuristic. Owner: Analytics — Due: 2025-09-25
6) SIE format variant/version required by accountant. Owner: Finance — Due: 2025-09-25
7) Languages (SV/EN) priority for admin UI and labels. Owner: PO — Due: 2025-09-25

## Decisions
- Python backend (Flask) + Celery + Redis + MySQL aligns with v2.0 plan.
- Admin SPA communicates only via `/ai/api/*` endpoints.
- Observability: Prometheus metrics + Grafana dashboards; JSON structured logs.
- Migrations: idempotent, additive; canonical order: unified → ai → invoice.

## Best Practices & References
- OCR/classification via worker queue; retry/backoff policies.
- JWT Bearer auth; CORS restricted.
- P95 latency targets <200ms for APIs; memory <100MB per process.
- TDD with contract tests first; coverage ≥90%.
