# Overlay Issues Review 2 (Follow-up)
- **Date:** 2025-10-19
- **Reviewer:** ChatGPT (Codex agent)

## Summary
The follow-up review confirms several previously flagged items are now fixed: the image stage remains intact, `imgRef` is finally declared, the payment/amount sections now wire their hover states, and the backend `PUT /modal` response returns refreshed box data. However, bidirectional highlighting is still incomplete. The new `buildHoverCandidates()` helper does not generate index-qualified keys, so overlays that use bracket notation (for example `items[0].name`) cannot be matched to item/proposal rows. In addition, the new row components lack any `.highlighted` / `.muted` CSS, and the “Övrigt” field still ignores hover handlers. Consequently, the core UX requirement—consistent overlay ⇄ field synchronisation—remains unmet.

## Frontend Findings
- PASS **Stage & forced portrait** – The overlay continues to render inside `.receipt-modal-image-stage`, and the preview image is requested with `?rotate=portrait`, keeping alignment stable (`main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx:906`, `…:1110`).
- PASS **`imgRef` hook added** – `const imgRef = React.useRef(null);` now lives alongside the other hooks (`…:694`), eliminating the previous runtime reference error.
- FAIL **`buildHoverCandidates` still misses indexed variants** – Although the helper is now defined (`…:25`), it only produces `[source.key, key, extras…]`. Overlay boxes for arrays (e.g. `items[0].name`, `proposals[1].account`) therefore never match: `resolveBoxField` normalises the box to `items[].name`, but none of the generated candidates normalise to the same value, so item/proposal cells stay unlinked (`…:1220`, `…:1267`). This blocks the highlight loop for every repeated section.
- PASS **Payment/amount grids wired** – `PAYMENT_FIELDS` and `AMOUNT_FIELDS` are finally used and each field wrapper now sets hover handlers plus `matchHighlight(...)` (`…:998-1035`, `…:1041-1072`).
- FAIL **“Övrigt” section still static** – The full-width field for `other_data` remains a plain `div` with no `matchHighlight` binding or hover callbacks, so its overlay (when present) still lacks a companion highlight (`…:1078-1096`).
- FAIL **Row-level CSS is missing highlight styles** – Item and proposal cells now append `highlighted` / `muted` classes (`…:1200-1338`), but `index.css` defines only the base selectors (`main-system/app-frontend/src/index.css:1288-1368`). Without `.receipt-item-cell-new.highlighted`, `.proposal-cell-new.highlighted`, etc., the new classes have no visual effect.
- WARN **Normalisation collision risk** – The fallback keys such as `items[${itemIndex}].name` feed into `matchHighlight`, but `normaliseFieldId` strips digits (`…:9-13`). If no overlay is present, hovering one row can still highlight peers because `items[0].name` and `items[1].name` both collapse to `items[].name`. Consider adding the index-aware candidate that the overlay generator uses, rather than relying on the stripped form.
- PASS **Diagnostics unchanged** – `window.__overlayDebug` is still populated for debugging / testing (`…:757`, `…:924`).

## API & Data Layer
- PASS **Modal GET unchanged** – `/ai/api/receipts/<rid>/modal` still returns boxes and counts as expected (`backend/src/api/receipts.py:1050-1066`).
- PASS **Modal PUT now returns fresh boxes** – The response payload includes `boxes` and `boxes_count`, so the frontend can finally refresh overlays after a save (`backend/src/api/receipts.py:1137-1158`).

## Image Orientation & Overlay
- PASS **Server-side rotation** – The image endpoint continues to enforce portrait rotation (`backend/src/api/receipts.py:1259-1294`), matching the frontend request strategy.
- WARN **No regression test yet** – There is still no evidence of an updated Playwright run for the overlay/orientation scenario. Complete the prescribed test once highlighting is fixed.

## Outstanding Actions
1. Extend `buildHoverCandidates()` (or the call sites) to include index-qualified keys such as `items[${index}].${key}` / `proposals[${index}].${key}` so `resolveBoxField` can actually match array overlays.
2. Add CSS rules for `.receipt-item-cell-new.highlighted`, `.receipt-item-cell-new.muted`, `.proposal-cell-new.highlighted`, and `.proposal-cell-new.muted` (and any other new class names) so the UI reflects hover state.
3. Wrap the “Övrigt” field in the same hover/highlight logic used elsewhere, including `resolveBoxField(buildHoverCandidates('other_data', …))` and `matchHighlight(...)` (`…:1078-1096`).
4. Review `normaliseFieldId` vs. fallback highlight keys to ensure repeated rows keep their highlights isolated when overlays are absent.
5. After implementing the above, rerun the required Playwright overlay-orientation scenario per `docs/TEST_RULES.md`.

## Test Status
- ❌ **2025-09-27_19-42_process_preview (chromium-ultrawide)** – Latest Playwright run in `web\test-results\_artifacts\2025-09-27_19-42_process_i-b1b52-ocess-preview-first-receipt-chromium-ultrawide` failed. The extracted trace logs show a React hook-order violation inside `ReceiptPreviewModal` (“React has detected a change in the order of Hooks…”, reported at `ReceiptPreviewModal.jsx:575:47`), followed by the component crashing (`test.trace`, timestamps 4 418–4 448 ms). Artifacts include `test-failed-1.png`, `video.webm`, and `trace.zip`. The `.last-run.json` status is `failed`.
- ▶️ **Action required** – Address the hook-order regression plus the outstanding highlight issues above, then rerun the mandated orientation Playwright scenario per `docs/TEST_RULES.md`.
