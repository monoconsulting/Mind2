# Agent Instruction: Fix overlay alignment + bidirectional hover highlight

## What’s wrong (root cause)

1. **Overlay misalignment**: Overlays are absolutely positioned inside `.receipt-modal-image-wrapper`, but the `<img>` is `object-fit: contain` with `max-width/max-height`, which often leaves letterboxing inside the wrapper. The wrapper is *larger* than the actual displayed image area, so `%` and `px` coordinates are applied to the wrong box.
2. **No hover coupling to fields**: The tables use `.receipt-modal-field` but never call `matchHighlight()` nor set hover handlers, so the “yellow” class never toggles when hovering a field.

## What we’ll do (safe, minimal changes)

- Introduce a **tight “stage” container** that shrinks exactly to the image’s rendered size and becomes the overlay’s positioning context.
- Keep your current `boxes` structure and `toCss` helper. We’ll just render overlays **inside the stage** instead of the wrapper.
- Add **hover handlers** and `.highlighted` class binding to the existing field rows (left & right tables) while respecting your 3-column layout and not altering scroll behavior.

------

## 1) Code patch — create a true positioning stage around the image

**File:** `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

### A) Add a ref for the image (top of component)

Find your React state/hooks area and add:

```jsx
// Keep the existing imports and state...
const imgRef = React.useRef(null);
```

*(This ref is used only to ensure the stage wraps the image element; we don’t need to read dimensions because the stage will naturally shrink-wrap to the image.)*

### B) Replace the image block with a “stage” container

**Before** (current, simplified):

```jsx
<div className="receipt-modal-center">
  <div className="receipt-modal-image-wrapper">
    {baseImageSrc ? (
      <img src={baseImageSrc} alt={`Kvitto ${receipt.id}`} className="receipt-modal-image" />
    ) : (
      <div className="receipt-modal-image-fallback">Ingen bild</div>
    )}
    {boxes.map((box, index) => {
      const overlayKey = box.field || `box-${index}`;
      // ...
      return (
        <div
          key={`${overlayKey}-${index}`}
          className={`receipt-modal-overlay ${matchHighlight(overlayKey)}`}
          style={{
            position: 'absolute',
            top: toCss(box.y ?? box.top ?? 0),
            left: toCss(box.x ?? box.left ?? 0),
            width: toCss(box.w ?? box.width ?? 0),
            height: toCss(box.h ?? box.height ?? 0),
          }}
          onMouseEnter={() => setHoverField(overlayKey)}
          onMouseLeave={() => setHoverField(null)}
        />
      );
    })}
  </div>
</div>
```

**After** (patch):

```jsx
<div className="receipt-modal-center">
  <div className="receipt-modal-image-wrapper">
    {baseImageSrc ? (
      // NEW: stage that shrink-wraps to the image exactly.
      <div className="receipt-modal-image-stage">
        <img
          ref={imgRef}
          src={baseImageSrc}
          alt={`Kvitto ${receipt.id}`}
          className="receipt-modal-image"
        />
        {boxes.map((box, index) => {
          const overlayKey = box.field || `box-${index}`;
          const toCss = (val) => {
            if (typeof val !== 'number') return '0%';
            if (val > 1) return `${val}px`;               // pixel coords supported
            const clamped = Math.min(Math.max(val, 0), 1); // normalized 0..1 → %
            return `${clamped * 100}%`;
          };
          return (
            <div
              key={`${overlayKey}-${index}`}
              className={`receipt-modal-overlay ${matchHighlight(overlayKey)}`}
              style={{
                // absolute now relative to the stage, which equals image box
                top: toCss(box.y ?? box.top ?? 0),
                left: toCss(box.x ?? box.left ?? 0),
                width: toCss(box.w ?? box.width ?? 0),
                height: toCss(box.h ?? box.height ?? 0),
              }}
              onMouseEnter={() => setHoverField(overlayKey)}
              onMouseLeave={() => setHoverField(null)}
            />
          );
        })}
      </div>
    ) : (
      <div className="receipt-modal-image-fallback">Ingen bild</div>
    )}
  </div>
</div>
```

> Why this works: `.receipt-modal-image-stage` shrink-wraps to the exact rendered `<img>` rectangle. Overlays are now absolutely positioned **inside the same box** the user sees, so both normalized (0..1) and px coordinates land perfectly.

------

## 2) CSS patch — add the stage container

**File:** `main-system/app-frontend/src/index.css`

Add the block below near your other `.receipt-modal-*` rules (you already have `.receipt-modal-image-wrapper` and `.receipt-modal-image`):

```css
/* Tight positioning stage that matches the rendered image box */
.receipt-modal-image-stage {
  position: relative;
  display: inline-block;     /* shrink-wrap to the image */
  line-height: 0;            /* remove inline gaps */
}

/* The image already has max-* and object-fit:contain set. Keep it. */
.receipt-modal-image {
  display: block;            /* ensures no extra baseline space */
}

/* Overlays are positioned within the stage */
.receipt-modal-overlay {
  position: absolute;
  border: 2px solid rgba(253, 224, 71, 0.7);
  background: transparent;
  box-shadow: 0 0 0 1px rgba(253, 224, 71, 0.3);
  transition: opacity 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
  z-index: 1;
}

.receipt-modal-overlay.highlighted {
  border-color: rgba(253, 224, 71, 0.95);
  box-shadow: 0 0 0 2px rgba(253, 224, 71, 0.4);
}
```

> Note: You already had `.receipt-modal-overlay` rules; if they exist, keep them—just ensure `.receipt-modal-image-stage` is added and overlays render inside it.

------

## 3) Code patch — link field rows to hover highlight

Right now, left/right table rows render as:

```jsx
<div key={field.key} className="receipt-modal-field">
  <label className="field-label">{field.label}</label>
  {editing ? ( ... ) : ( ... )}
</div>
```

You already have:

```jsx
const [hoverField, setHoverField] = React.useState(null);
const matchHighlight = (key) => {
  if (!hoverField || !key) return '';
  return normaliseFieldId(hoverField) === normaliseFieldId(key) ? 'highlighted' : 'muted';
};
```

We’ll bind `matchHighlight(field.key)` and add hover handlers so **hovering a field highlights its overlay** and **hovering an overlay highlights the field** (you already set hover on overlays).

### A) Left-column info blocks

Find the map rendering these fields (around lines ~900, ~943, ~977 and similar). Replace the wrapper `<div>` with:

```jsx
<div
  key={field.key}
  className={`receipt-modal-field ${matchHighlight(field.key)}`}
  onMouseEnter={() => setHoverField(field.key)}
  onMouseLeave={() => setHoverField(null)}
>
  <label className="field-label">{field.label}</label>
  {editing ? ( ... ) : ( ... )}
</div>
```

### B) Any additional field grids (right column, totals/VAT, payment fields)

Do the same for those mapped blocks:

```jsx
<div
  key={field.key}
  className={`receipt-modal-field ${matchHighlight(field.key)}`}
  onMouseEnter={() => setHoverField(field.key)}
  onMouseLeave={() => setHoverField(null)}
>
  <label className="field-label">{field.label}</label>
  {editing ? ( ... ) : ( ... )}
</div>
```

> You do **not** need to change labels/inputs/components inside; we only add class binding + hover handlers on the outer field container.

### C) (Optional) Item rows

If you want per-item line hover to sync with overlays (when there are item-level boxes), give each row a stable key like `items[${itemIndex}]`:

```jsx
<div
  className={`receipt-item-row ${matchHighlight(`items[${itemIndex}]`)}`}
  onMouseEnter={() => setHoverField(`items[${itemIndex}]`)}
  onMouseLeave={() => setHoverField(null)}
>
  ...
</div>
```

…and make sure the corresponding overlay uses `box.field = "items[<index>]"` (or your existing naming) so `normaliseFieldId()` aligns.

------

## 4) Keep your current normalization logic

You already have:

```jsx
function normaliseFieldId(value) {
  if (!value || typeof value !== 'string') return '';
  const lower = value.toLowerCase().trim();
  const withoutPrefix = lower.replace(/^(receipt|unified_files|r..._items|accounting_proposals|items|line_items|proposals)\./i, '');
  const withoutBrackets = withoutPrefix.replace(/[\d+]/g, '');
  return withoutBrackets;
}
```

This is fine as long as the `box.field` and `field.key` share consistent semantics. If your overlay fields are like `receipt.total_amount` and the table keys are `total_amount`, the helper already bridges that gap. If any fields still don’t match, adjust the **patterns in `normaliseFieldId`** (not the UI layout).

------

## 5) Visual consistency (same yellow everywhere)

You already have styles for `.receipt-modal-field.highlighted`. If not, ensure they mirror the overlay’s yellow:

**File:** `main-system/app-frontend/src/index.css` (you already have a similar block)

```css
.receipt-modal-field.highlighted {
  border-color: rgba(253, 224, 71, 0.9);
  background: rgba(253, 224, 71, 0.12);
  box-shadow: 0 0 0 2px rgba(253, 224, 71, 0.2) inset;
}
```

That makes the left/right table rows clearly “in sync” with the yellow overlays.

------

## 6) Behavior guarantees (no layout/scroll changes)

- We **do not** change the column grid, sizes, or scroll containers.
- The new `.receipt-modal-image-stage` lives **inside** the existing `.receipt-modal-image-wrapper`, so the overall center column keeps its dimensions.
- Overlays are still absolute, just positioned relative to the **true image rectangle**.

------

## 7) Quick verification checklist

1. Open any receipt with boxes.
2. Hover an overlay → the matching field in left/right column turns yellow.
3. Hover a field in the left/right column → the corresponding overlay turns yellow.
4. Resize the modal/browser → overlays remain pixel-perfect over the image.
5. No change to the three columns’ layout or scrolling.

------

If you want, I can produce a single consolidated patch chunk for `ReceiptPreviewModal.jsx` that inlines all the replacements above (with exact line anchors based on your current file).