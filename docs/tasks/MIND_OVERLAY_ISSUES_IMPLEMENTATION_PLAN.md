# Task 5.4 - Overlay Issues Implementation Plan
## Komplett Steg-för-Steg Guide

**Datum:** 2025-10-19
**Baserad på:**
- Kodanalys av ReceiptPreviewModal.jsx
- MIND_OVERLAY_ISSUES.md instruktioner
- MIND_OVERLAY_ISSUES_REVIEW_1.md findings
- Playwright trace analysis

---

## PRE-FLIGHT CHECKLIST

Innan du börjar, verifiera:
- [ ] Du har läst MIND_OVERLAY_ISSUES_REVIEW_1.md
- [ ] Backend och frontend är igång (`mind_docker_compose_up.bat`)
- [ ] Dev-server körs på port 5169 (för hot-reload)
- [ ] Du har backup av filer (git commit eller copy)
- [ ] Playwright trace viewer är tillgänglig för verifiering

---

## PHASE 1: IMAGE STAGE WRAPPER (KRITISK PRIO)

**Mål:** Fixa overlay-positionering genom att wrappa bilden i `.receipt-modal-image-stage`

**Estimerad tid:** 20 minuter

### STEG 1.1: Lägg till imgRef i component state

**Fil:** `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

**Plats:** Efter rad 633 (där `hoverField` state deklareras)

**Åtgärd:**
```jsx
const [hoverField, setHoverField] = React.useState(null);
const imgRef = React.useRef(null);  // ← LÄGG TILL DENNA RAD
```

**Verifiering:**
- [ ] Ingen syntax error i console
- [ ] Component renderar fortfarande

---

### STEG 1.2: Wrappa bilden i stage container

**Fil:** `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

**Plats:** Rad 1030-1064 (image rendering section)

**NUVARANDE KOD (rad 1030-1064):**
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
      const toCss = (val) => {
        if (typeof val !== 'number') {
          return '0%';
        }
        if (val > 1) {
          return `${val}px`;
        }
        const clamped = Math.min(Math.max(val, 0), 1);
        return `${clamped * 100}%`;
      };
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

**NY KOD (ersätt hela blocket):**
```jsx
<div className="receipt-modal-center">
  <div className="receipt-modal-image-wrapper">
    {baseImageSrc ? (
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
            if (typeof val !== 'number') {
              return '0%';
            }
            if (val > 1) {
              return `${val}px`;
            }
            const clamped = Math.min(Math.max(val, 0), 1);
            return `${clamped * 100}%`;
          };
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
    ) : (
      <div className="receipt-modal-image-fallback">Ingen bild</div>
    )}
  </div>
</div>
```

**Ändringar:**
1. ✅ Lagt till `<div className="receipt-modal-image-stage">` wrapper
2. ✅ Flyttat `<img>` inuti stage
3. ✅ Lagt till `ref={imgRef}` på img
4. ✅ Flyttat `boxes.map()` inuti stage (efter img)
5. ✅ Stängt stage-div före fallback-div

**Verifiering:**
- [ ] Modal öppnas utan errors
- [ ] Bilden visas korrekt
- [ ] Overlays renderas (även om de kan vara fel placerade ännu)
- [ ] Dev console visar inga warnings

---

## PHASE 2: FIELD HOVER HANDLERS - VÄNSTER KOLUMN

**Mål:** Aktivera hover-highlighting för alla fields i vänster kolumn

**Estimerad tid:** 30 minuter

### STEG 2.1: Företagsinformation (Box 1)

**Fil:** `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

**Plats:** Rad ~904-922

**NUVARANDE KOD:**
```jsx
].map((field) => {
  const sourceData = field.source === 'company' ? companyData : receiptData;
  const draftData = field.source === 'company' ? companyDraft : receiptDraft;
  return (
    <div key={field.key} className="receipt-modal-field">
      <label className="field-label">{field.label}</label>
      {editing ? (
        <input
          className="dm-input"
          value={draftData[field.key] ?? ''}
          onChange={(event) => field.source === 'company' ? updateCompanyDraft(field.key, event.target.value) : updateReceiptDraft(field.key, event.target.value)}
          disabled={saving}
        />
      ) : (
        <div className="field-value">{sourceData[field.key] || '-'}</div>
      )}
    </div>
  );
})}
```

**NY KOD:**
```jsx
].map((field) => {
  const sourceData = field.source === 'company' ? companyData : receiptData;
  const draftData = field.source === 'company' ? companyDraft : receiptDraft;
  return (
    <div
      key={field.key}
      className={`receipt-modal-field ${matchHighlight(field.key)}`}
      onMouseEnter={() => setHoverField(field.key)}
      onMouseLeave={() => setHoverField(null)}
    >
      <label className="field-label">{field.label}</label>
      {editing ? (
        <input
          className="dm-input"
          value={draftData[field.key] ?? ''}
          onChange={(event) => field.source === 'company' ? updateCompanyDraft(field.key, event.target.value) : updateReceiptDraft(field.key, event.target.value)}
          disabled={saving}
        />
      ) : (
        <div className="field-value">{sourceData[field.key] || '-'}</div>
      )}
    </div>
  );
})}
```

**Ändringar:**
- ✅ Lagt till `${matchHighlight(field.key)}` i className
- ✅ Lagt till `onMouseEnter={() => setHoverField(field.key)}`
- ✅ Lagt till `onMouseLeave={() => setHoverField(null)}`

**Påverkade fields:**
- name, orgnr, address, address2, zip, city, country, www, phone, email

**Verifiering:**
- [ ] Hover över field → field blir gul
- [ ] Hover över field → motsvarande overlay blir gul (om box finns)
- [ ] Andra overlays blir muted (transparent)

---

### STEG 2.2: Betalningstyp (Box 2)

**Fil:** `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

**Plats:** Rad ~930-960

**NUVARANDE KOD:**
```jsx
].map((field) => (
  <div key={field.key} className="receipt-modal-field">
    <label className="field-label">{field.label}</label>
    {editing ? (
      <input
        className="dm-input"
        value={receiptDraft[field.key] ?? ''}
        onChange={(event) => updateReceiptDraft(field.key, event.target.value)}
        disabled={saving}
      />
    ) : field.key === 'purchase_datetime' ? (
      <div className="field-value">{formatDate(receiptData.purchase_datetime)}</div>
    ) : (
      <div className="field-value">{receiptData[field.key] || '-'}</div>
    )}
  </div>
))
```

**NY KOD:**
```jsx
].map((field) => (
  <div
    key={field.key}
    className={`receipt-modal-field ${matchHighlight(field.key)}`}
    onMouseEnter={() => setHoverField(field.key)}
    onMouseLeave={() => setHoverField(null)}
  >
    <label className="field-label">{field.label}</label>
    {editing ? (
      <input
        className="dm-input"
        value={receiptDraft[field.key] ?? ''}
        onChange={(event) => updateReceiptDraft(field.key, event.target.value)}
        disabled={saving}
      />
    ) : field.key === 'purchase_datetime' ? (
      <div className="field-value">{formatDate(receiptData.purchase_datetime)}</div>
    ) : (
      <div className="field-value">{receiptData[field.key] || '-'}</div>
    )}
  </div>
))
```

**Påverkade fields:**
- purchase_datetime, receipt_number, payment_type, expense_type
- credit_card_number, credit_card_last_4_digits, credit_card_type
- credit_card_brand_full, credit_card_brand_short, credit_card_payment_variant
- credit_card_token, credit_card_entering_mode

**Verifiering:**
- [ ] Samma hover-beteende som steg 2.1

---

### STEG 2.3: Belopp (Box 3)

**Fil:** `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

**Plats:** Rad ~967-994

**NUVARANDE KOD:**
```jsx
].map((field) => (
  <div key={field.key} className="receipt-modal-field">
    <label className="field-label">{field.label}</label>
    {editing ? (
      <input
        className="dm-input"
        value={receiptDraft[field.key] ?? ''}
        onChange={(event) => updateReceiptDraft(field.key, event.target.value)}
        disabled={saving}
      />
    ) : field.format === 'currency' ? (
      <div className="field-value">{formatCurrency(Number(receiptData[field.key] || 0))}</div>
    ) : (
      <div className="field-value">{receiptData[field.key] || '-'}</div>
    )}
  </div>
))
```

**NY KOD:**
```jsx
].map((field) => (
  <div
    key={field.key}
    className={`receipt-modal-field ${matchHighlight(field.key)}`}
    onMouseEnter={() => setHoverField(field.key)}
    onMouseLeave={() => setHoverField(null)}
  >
    <label className="field-label">{field.label}</label>
    {editing ? (
      <input
        className="dm-input"
        value={receiptDraft[field.key] ?? ''}
        onChange={(event) => updateReceiptDraft(field.key, event.target.value)}
        disabled={saving}
      />
    ) : field.format === 'currency' ? (
      <div className="field-value">{formatCurrency(Number(receiptData[field.key] || 0))}</div>
    ) : (
      <div className="field-value">{receiptData[field.key] || '-'}</div>
    )}
  </div>
))
```

**Påverkade fields:**
- currency, exchange_rate, gross_amount, net_amount
- gross_amount_sek, net_amount_sek
- total_vat_25, total_vat_12, total_vat_6

**Verifiering:**
- [ ] Samma hover-beteende som tidigare

---

## PHASE 3: FIELD HOVER HANDLERS - HÖGER KOLUMN (OPTIONAL)

**Mål:** Aktivera hover för item-rader

**Estimerad tid:** 15 minuter

**Prioritet:** MEDIUM (kan göras senare)

### STEG 3.1: Item Cards Hover

**Fil:** `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

**Plats:** Rad ~1084

**NUVARANDE KOD:**
```jsx
return (
  <div key={`item-${itemIndex}`} className="receipt-item-card-new">
    <div className="receipt-item-header-new">RAD {itemIndex + 1}</div>
    {/* ... rest of item content ... */}
  </div>
);
```

**NY KOD:**
```jsx
return (
  <div
    key={`item-${itemIndex}`}
    className={`receipt-item-card-new ${matchHighlight(`items[${itemIndex}]`)}`}
    onMouseEnter={() => setHoverField(`items[${itemIndex}]`)}
    onMouseLeave={() => setHoverField(null)}
  >
    <div className="receipt-item-header-new">RAD {itemIndex + 1}</div>
    {/* ... rest of item content ... */}
  </div>
);
```

**VIKTIGT:** Detta fungerar endast om backend skickar boxes med format:
```json
{
  "field": "items[0]",
  "x": 0.1,
  "y": 0.2,
  "w": 0.3,
  "h": 0.05
}
```

**Verifiering:**
- [ ] Om item-level boxes finns: hover över rad → overlay highlightas
- [ ] Om inga item-boxes: ingen effekt (OK)

---

## PHASE 4: TESTING & VERIFICATION

**Estimerad tid:** 30 minuter

### STEG 4.1: Lokal Manual Testing

**Åtgärd:**
1. Starta dev-server (port 5169)
2. Öppna browser: http://localhost:5169
3. Logga in (adminadmin)
4. Gå till Process
5. Klicka "Förhandsgranska kvitto" på valfritt kvitto

**Test Cases:**

#### TC1: Overlay Alignment
- [ ] Overlays är exakt över rätt text i bilden
- [ ] Ingen offset horisontellt
- [ ] Ingen offset vertikalt
- [ ] Testat med portrait-bild
- [ ] Testat med landscape-bild
- [ ] Resize browser → overlays följer bilden

#### TC2: Overlay → Field Highlight
- [ ] Hover över overlay → overlay blir gul
- [ ] Hover över overlay → motsvarande field (vänster) blir gul
- [ ] Hover över overlay → andra overlays blir muted (opacity 0.35)
- [ ] Lämna hover → allt återgår till normal

#### TC3: Field → Overlay Highlight
- [ ] Hover över field (vänster) → field blir gul
- [ ] Hover över field (vänster) → motsvarande overlay blir gul
- [ ] Hover över field (vänster) → andra overlays blir muted
- [ ] Lämna hover → allt återgår till normal

#### TC4: Rapid Hover Switching
- [ ] Hover snabbt mellan olika fields
- [ ] Highlight uppdateras utan lag
- [ ] Endast en field/overlay pair är highlighted åt gången
- [ ] Inga visuella glitches

#### TC5: Edge Cases
- [ ] Field utan box → endast field highlightas (no error)
- [ ] Box utan field → endast overlay highlightas (no error)
- [ ] Tom boxes array → modal fungerar ändå
- [ ] >20 overlays → performance OK

---

### STEG 4.2: Playwright E2E Test

**Åtgärd:**
Kör befintligt test med trace:

```bash
cd E:\projects\Mind2\web
npx playwright test tests/2025-09-27_19-42_receipt_image_orientation_and_zoom.spec.ts --headed --trace on
```

**Verifiering:**
- [ ] Test passerar utan errors
- [ ] Modal öppnas på 5:e kvittot
- [ ] Modal stannar öppen i 5 sekunder
- [ ] Trace visar inga console errors
- [ ] Screenshots i trace visar korrekt overlay alignment

**Om test failar:**
1. Öppna trace viewer: `npx playwright show-trace test-results/*/trace.zip`
2. Inspektera screenshots vid modal-öppning
3. Kolla console logs för errors
4. Verifiera DOM structure i trace

---

### STEG 4.3: Cross-Browser Testing (Optional)

**Åtgärd:**
```bash
# Firefox
npx playwright test --project=firefox --headed

# WebKit (Safari)
npx playwright test --project=webkit --headed
```

**Verifiering:**
- [ ] Firefox: samma beteende som Chrome
- [ ] WebKit: samma beteende som Chrome

---

## PHASE 5: CLEANUP & DOCUMENTATION

**Estimerad tid:** 15 minuter

### STEG 5.1: Code Review

**Checklist:**
- [ ] Inga console.log() debugs kvar
- [ ] Inga commented-out code blocks
- [ ] Indentation konsekvent
- [ ] Inga syntax warnings i IDE
- [ ] ESLint happy (om ni kör det)

---

### STEG 5.2: Git Commit

**Åtgärd:**
```bash
cd E:\projects\Mind2
git status
git add main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx
git commit -m "fix: Implement overlay alignment and bidirectional hover highlighting

- Add .receipt-modal-image-stage wrapper for accurate overlay positioning
- Add imgRef to track image element
- Implement hover handlers on all receipt fields (30+ fields)
- Fix misalignment caused by object-fit:contain letterboxing
- Enable bidirectional highlight: field↔overlay synchronization

Fixes: Task 5.4 - Overlay alignment issues
Related: MIND_OVERLAY_ISSUES.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Verifiering:**
- [ ] Commit skapad utan errors
- [ ] Commit message följer convention
- [ ] Rätt filer inkluderade

---

### STEG 5.3: Update Task Documentation

**Åtgärd:**
Uppdatera `docs/tasks/MIND_TASKS.md` task 5.4 status:

```markdown
## 5.4 ✅ Fix overlay alignment + bidirectional hover highlight

**Status:** COMPLETED (2025-10-19)

**Implementation:**
- Image stage wrapper implemented
- All field hover handlers added (vänster + höger kolumn)
- Bidirectional highlighting fungerar
- Tested with Playwright

**Files Changed:**
- main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx

**Verification:**
- Manual testing: ✅
- Playwright E2E: ✅
- Alignment accuracy: ✅
```

---

## TROUBLESHOOTING

### Problem 1: Overlays inte synliga efter stage-wrap

**Symptom:** Modal öppnas men inga overlays syns

**Debug:**
```jsx
// Temporär debug i ReceiptPreviewModal.jsx rad ~700
console.log('Boxes:', boxes);
console.log('Boxes count:', boxes.length);
```

**Möjliga orsaker:**
1. `boxes` array är tom → kolla API response `/api/receipts/:id/modal`
2. CSS z-index konflikt → inspektera i DevTools
3. Stage wrapper höjd = 0 → kolla `.receipt-modal-image-stage` CSS

**Lösning:**
- Verifiera API returnerar boxes
- Verifiera `.receipt-modal-image-stage` har `display: inline-block`

---

### Problem 2: Hover fungerar inte på vissa fields

**Symptom:** Några fields reagerar inte på hover

**Debug:**
```jsx
// Temporär debug i field render
onMouseEnter={() => {
  console.log('Hover field:', field.key);
  setHoverField(field.key);
}}
```

**Möjliga orsaker:**
1. `field.key` är undefined → kolla field definition
2. `matchHighlight()` returnerar fel → kolla normalization
3. CSS `.highlighted` appliceras inte → inspektera i DevTools

**Lösning:**
- Verifiera alla fields har `key` property
- Testa `normaliseFieldId()` med field.key och box.field

---

### Problem 3: Alignment fortfarande fel

**Symptom:** Overlays är offset från bilden

**Debug:**
1. Öppna DevTools
2. Inspektera `.receipt-modal-image-stage`
3. Verifiera att overlays är **barn** till stage, inte wrapper

**Möjliga orsaker:**
1. Overlays fortfarande utanför stage → kod inte uppdaterad korrekt
2. CSS `position: relative` saknas på stage
3. Bilden har margin/padding → inspektera computed styles

**Lösning:**
- Verifiera DOM structure: `wrapper > stage > (img + overlays)`
- Verifiera `.receipt-modal-image-stage` har `position: relative`

---

### Problem 4: Performance issues med många overlays

**Symptom:** Lag vid hover när >50 overlays

**Debug:**
```jsx
// Mät render time
const start = performance.now();
// ... render logic ...
console.log('Render time:', performance.now() - start);
```

**Lösning (om nödvändigt):**
1. Debounce hover handlers:
```jsx
const debouncedSetHover = React.useMemo(
  () => debounce(setHoverField, 16), // 60fps
  []
);
```

2. Memoize matchHighlight:
```jsx
const highlightClass = React.useMemo(
  () => matchHighlight(field.key),
  [hoverField, field.key]
);
```

---

## POST-IMPLEMENTATION CHECKLIST

Efter alla steg är klara:

- [ ] Phase 1: Image stage wrapper ✅
- [ ] Phase 2: Field hover handlers (vänster) ✅
- [ ] Phase 3: Item hover (optional) ✅/⏭️
- [ ] Phase 4: Testing passed ✅
- [ ] Phase 5: Git commit + docs ✅
- [ ] Trace screenshots visar korrekt alignment ✅
- [ ] Manual testing i alla scenarios ✅
- [ ] Inga console errors ✅
- [ ] Code review OK ✅
- [ ] Ready for production ✅

---

## ESTIMATED TOTAL TIME

**Minimum (kritiska fixes):** 50 minuter
- Phase 1: 20 min
- Phase 2: 30 min

**Recommended (inkl testing):** 1h 35min
- Phase 1: 20 min
- Phase 2: 30 min
- Phase 4: 30 min
- Phase 5: 15 min

**Full (inkl optional):** 1h 50min
- Phase 1: 20 min
- Phase 2: 30 min
- Phase 3: 15 min
- Phase 4: 30 min
- Phase 5: 15 min

---

## NEXT STEPS

1. ✅ Läs denna plan helt
2. ⏭️ Gör en backup/commit innan start
3. ⏭️ Kör Phase 1 (kritisk)
4. ⏭️ Testa alignment efter Phase 1
5. ⏭️ Kör Phase 2 (kritisk)
6. ⏭️ Testa full hover efter Phase 2
7. ⏭️ Kör Phase 4 (testing)
8. ⏭️ Om allt OK: Phase 5 (commit)
9. ⏭️ Om problem: se Troubleshooting

---

**Plan Version:** 1.0
**Status:** READY TO EXECUTE
**Created:** 2025-10-19
