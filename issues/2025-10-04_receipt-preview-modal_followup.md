# Receipt Preview Modal still lacks interactive editing and yellow OCR mapping

## Summary
- The current modal (`main-system/app-frontend/src/ui/pages/Process.jsx::PreviewModal`) only renders the receipt image with blue overlays and no surrounding data columns.
- There is no editable receipt data panel, no items/proposals list, and no Edit → Save workflow.
- Hover linking between OCR boxes and the left/right text fields is missing, and markers remain blue instead of yellow.
- No backend endpoints were added to persist edits to `unified_files`, `receipt_items`, or `accounting_proposals`.

## Impact
Users still cannot review or adjust receipt data inside the preview modal, defeating the purpose of Issue #14. Editing continues to require out-of-band tooling and loses OCR-to-data traceability.

## How to Reproduce
1. Go to Kvitton (Receipts) in the UI.
2. Open any receipt preview modal.
3. Observe the single-column modal with only an image and blue overlays; no editable panels or hover linkage exist.

## Expected
- Three-column layout (receipt metadata left, image centre, items + accounting proposals right).
- Yellow OCR markers with bi-directional hover highlight.
- Edit button enabling inline changes and Save/Cancel, persisting updates via new backend endpoints.

## Suggested Fix
- Implement the required layout and state management per Issue #14.
- Add backend API endpoints for updating `unified_files`, `receipt_items`, and `accounting_proposals` records.
- Update UI to use yellow markers and wire hover/highlight synchronization.
- Provide unit/integration tests for data mapping and hover behaviour.

## References
- GitHub Issue #14: https://github.com/monoconsulting/Mind2/issues/14
- Current modal implementation: main-system/app-frontend/src/ui/pages/Process.jsx (function `PreviewModal`).
