# Resume Process Investigation (2025-10-22)

## Summary
- Clicking either **Återuppta** per receipt or the bulk **Återuppta alla** on the Process view leaves receipts unchanged and shows the error banner *"Kunde inte återuppta bearbetning"* even though the UI briefly flips items to `pending`.
- The bundled Playwright regression `web/tests/run-resume-receipts-test.bat` currently reports all scenarios as passing, so the failure is escaping automated detection.

## Reproduction
- `cmd /c web\tests\run-resume-receipts-test.bat` (22.9s) ✔️ – all four specs pass, confirming the test suite does not assert on the actual resume side effects.
- Manual inspection of the Process page reproduces the error banner on every resume attempt.

## Findings
- **Frontend call path** – `main-system/app-frontend/src/ui/pages/Process.jsx:1401`-`1477` invokes `api.fetch("/ai/api/ingest/process/${fileId}/resume", { method: "POST" })` for both single and bulk resume buttons and expects a JSON response containing `{ queued: true }`.
- **UI state masking** – `resetReceiptForResume` pre-emptively rewrites the in-memory receipt item to `pending` before the network request resolves (`Process.jsx:1103`-`1125`), so visually the row appears to resume even when the request later fails. The Playwright test only asserts that the Process button is still visible, so it considers the flow successful.
- **Backend gap** – There is no Flask route that serves `POST /ingest/process/<file_id>/resume`. `rg --fixed-strings -n '/ingest/process' backend/src` returned no matches, and the only reference is a utility script (`scripts/trigger_ocr_all.py:41`) that would likewise hit a missing endpoint.
- **Existing ingest blueprint** – `backend/src/api/ingest.py:86` defines the upload entrypoint but provides no resume handler. The ai_processing blueprint only exposes `/process/batch` (`backend/src/api/ai_processing.py:716`), so the proxy target `/ai/api/ingest/process/*` inevitably answers 404.
- Because the resume API never responds with `queued: true`, the frontend displays the failure banner, and no workflow is dispatched.

## Root Cause
Frontend resume actions point to `/ai/api/ingest/process/<file_id>/resume`, but the backend offers no matching endpoint or task hook to re-queue receipts. Every resume attempt therefore fails at the network layer.

## Impact
- Users cannot restart stalled receipts, blocking recovery from paused or errored states.
- Bulk resume is equally broken.
- Automated regression coverage is ineffective, masking the problem.

## Recommended Plan
1. **Implement backend resume endpoint** – Add a Flask route (e.g. in `api/ingest.py`) that validates the receipt, resets its AI status, creates a new workflow run via `services.workflow_runs.create_workflow_run`, and dispatches it with `services.tasks.dispatch_workflow`, returning `{ "queued": true, ... }` on success.
2. **Align frontend endpoint usage** – Update `Process.jsx` to hit the new backend route and emit success banners only after the API confirms queuing. Avoid mutating local item state until the call succeeds.
3. **Strengthen automated tests** – Extend `web/tests/resume-receipts.spec.ts` to assert on the success banner or refreshed status, and add a backend integration test that exercises the resume endpoint against a fixture receipt.
4. **Add resilience checks** – Log failures server-side and surface actionable messages in the UI so support can distinguish 404 (missing endpoint) from workflow dispatch errors.

