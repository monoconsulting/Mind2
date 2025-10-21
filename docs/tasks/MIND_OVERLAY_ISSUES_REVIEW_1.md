# Task 5.4 - Overlay Issues Implementation Review

**Datum:** 2025-10-19
**Reviewer:** Claude Agent
**Task Reference:** @docs/tasks/MIND_TASKS.md Task 5.4
**Instruktioner:** @docs/tasks/MIND_OVERLAY_ISSUES.md

---

## Executive Summary

Task 5.4 är **DELVIS IMPLEMENTERAD**. De viktigaste komponenterna för overlay-positionering är på plats, men **kritiska hover-interaktioner saknas helt** för field-elementen. Detta gör att den tvåvägshöjdmarkeringen (hovering över fält markerar overlay och vice versa) inte fungerar.

### Status Overview
- ✅ **KLAR:** Overlay positioning stage (CSS och JSX struktur)
- ✅ **KLAR:** Overlay hover handlers
- ✅ **KLAR:** State management för hover
- ❌ **SAKNAS:** Field hover handlers i vänster kolumn
- ❌ **SAKNAS:** Field hover handlers i höger kolumn
- ⚠️ **DELVIS:** CSS highlight-klasser (finns men används inte fullt ut)

---

## 1. Detaljerad Analys av Implementerad Kod

### 1.1 ✅ CSS - Positioning Stage (IMPLEMENTERAT)

**Fil:** `main-system/app-frontend/src/index.css`

**Status:** ✅ Korrekt implementerat enligt instruktioner

**Kod (rad 940-944):**
```css
.receipt-modal-image-stage {
  position: relative;
  display: inline-block;
  line-height: 0;
}
```

**Verifiering:**
- Stage-containern finns och följer exakt spec från instruktionerna
- `position: relative` skapar korrekt positioneringskontext
- `display: inline-block` ger shrink-wrap beteende
- `line-height: 0` eliminerar inline gaps

**Övriga CSS-komponenter:**
```css
/* Rad 960-973 - Overlay styles */
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
  box-shadow: 0 0 0 2px rgba(253, 224, 71, 0.45);
  z-index: 3;
}
```

✅ Korrekt yellow färgschema (253, 224, 71)
✅ Highlighted och muted states finns

```css
/* Rad 899-903 - Field highlights */
.receipt-modal-field.highlighted {
  border-color: rgba(253, 224, 71, 0.9);
  background: rgba(253, 224, 71, 0.12);
  box-shadow: 0 0 0 2px rgba(253, 224, 71, 0.2) inset;
}
```

✅ Samma färgschema för field highlights

---

### 1.2 ❌ JSX - Image Stage Wrapper (INTE IMPLEMENTERAT)

**Fil:** `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

**Status:** ❌ SAKNAS - Stage wrapper används inte

**Nuvarande kod (rad 1030-1064):**
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

**Problem:**
1. ❌ `<img>` taggen är **inte wrapped** i `.receipt-modal-image-stage` div
2. ❌ Overlays renderas som siblings till `<img>` istället för inuti stage
3. ❌ Ingen `imgRef` reference har skapats (som nämns i instruktionerna rad 26)

**Förväntad struktur enligt instruktioner (rad 68-104):**
```jsx
<div className="receipt-modal-image-wrapper">
  {baseImageSrc ? (
    <div className="receipt-modal-image-stage">  {/* SAKNAS */}
      <img
        ref={imgRef}  {/* SAKNAS */}
        src={baseImageSrc}
        alt={`Kvitto ${receipt.id}`}
        className="receipt-modal-image"
      />
      {boxes.map((box, index) => {
        /* overlays här */
      })}
    </div>
  ) : (
    <div className="receipt-modal-image-fallback">Ingen bild</div>
  )}
</div>
```

**Konsekvenser:**
- Overlays är fortfarande positionerade relativt till `.receipt-modal-image-wrapper` som är större än själva bilden
- Detta leder till **misalignment** när bilden har letterboxing pga `object-fit: contain`
- Procentbaserade koordinater appliceras på fel box

---

### 1.3 ✅ State Management och Helper Functions (IMPLEMENTERAT)

**Fil:** `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

**Status:** ✅ Fullständigt implementerat

**Kod (rad 633):**
```jsx
const [hoverField, setHoverField] = React.useState(null);
```

✅ Hover state finns

**Kod (rad 701-706):**
```jsx
const matchHighlight = (key) => {
  if (!hoverField || !key) {
    return '';
  }
  return normaliseFieldId(hoverField) === normaliseFieldId(key) ? 'highlighted' : 'muted';
};
```

✅ Helper function korrekt implementerad
✅ Returnerar 'highlighted', 'muted' eller '' som förväntat

**Kod (rad 6-14) - normaliseFieldId:**
```jsx
function normaliseFieldId(value) {
  if (!value || typeof value !== 'string') {
    return '';
  }
  const lower = value.toLowerCase().trim();
  const withoutPrefix = lower.replace(/^(receipt|unified_files|receipt_items|accounting_proposals|items|line_items|proposals)./i, '');
  const withoutBrackets = withoutPrefix.replace(/[\d+]/g, '');
  return withoutBrackets;
}
```

✅ Normalization logic finns och fungerar för att matcha field keys med box.field

---

### 1.4 ✅ Overlay Hover Handlers (IMPLEMENTERAT)

**Fil:** `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

**Status:** ✅ Korrekt implementerat

**Kod (rad 1059-1060):**
```jsx
onMouseEnter={() => setHoverField(overlayKey)}
onMouseLeave={() => setHoverField(null)}
```

✅ Overlays har hover handlers
✅ Använder korrekt `overlayKey` från `box.field || `box-${index}``
✅ Kallar `setHoverField` för att uppdatera state

**Kod (rad 1051):**
```jsx
className={`receipt-modal-overlay ${matchHighlight(overlayKey)}`}
```

✅ Använder `matchHighlight()` för att sätta klasser dynamiskt

---

### 1.5 ❌ Field Hover Handlers (INTE IMPLEMENTERAT)

**Fil:** `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

**Status:** ❌ SAKNAS HELT

Detta är det **största problemet** med implementeringen.

#### 1.5.1 Vänster kolumn - Företagsinformation

**Nuvarande kod (rad 908):**
```jsx
<div key={field.key} className="receipt-modal-field">
  <label className="field-label">{field.label}</label>
  {editing ? (
    <input ... />
  ) : (
    <div className="field-value">{sourceData[field.key] || '-'}</div>
  )}
</div>
```

❌ Ingen `matchHighlight(field.key)` i className
❌ Inga hover handlers (`onMouseEnter`/`onMouseLeave`)

**Förväntad kod enligt instruktioner (rad 182-192):**
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

**Påverkade sektioner:**
- Företagsinformation (rad ~904-922)
- Betalningstyp (rad ~930-960)
- Belopp (rad ~967-994)

Totalt **~30+ fields** i vänster kolumn saknar hover handlers.

#### 1.5.2 Höger kolumn - Items och kontering

**Nuvarande kod (rad 1084-1123):**
```jsx
<div key={`item-${itemIndex}`} className="receipt-item-card-new">
  <div className="receipt-item-header-new">RAD {itemIndex + 1}</div>
  <div className="receipt-item-grid-new">
    {ITEM_DETAIL_FIELDS.map((field) => {
      return (
        <div key={`${field.key}-${itemIndex}`} className="receipt-item-cell-new">
          <span className="cell-label-new">{field.label}</span>
          {/* ... */}
        </div>
      );
    })}
  </div>
</div>
```

❌ Item cards saknar hover handlers
❌ Individual cells saknar hover handlers
❌ Ingen användning av `matchHighlight()` i item-relaterade komponenter

**Förväntad kod enligt instruktioner (rad 213-226):**
```jsx
<div
  className={`receipt-item-row ${matchHighlight(`items[${itemIndex}]`)}`}
  onMouseEnter={() => setHoverField(`items[${itemIndex}]`)}
  onMouseLeave={() => setHoverField(null)}
>
  ...
</div>
```

---

## 2. Konsekvenser av Saknade Implementationer

### 2.1 Användarupplevelse

**Nuvarande beteende:**
- ✅ Hovering över overlay → overlay blir highlighted (fungerar)
- ❌ Hovering över overlay → motsvarande field blir highlighted (fungerar INTE)
- ❌ Hovering över field → motsvarande overlay blir highlighted (fungerar INTE)
- ❌ Hovering över field → field blir highlighted (fungerar INTE)

**Detta innebär att endast 25% av den önskade interaktionen fungerar.**

### 2.2 Overlay Alignment

Eftersom `.receipt-modal-image-stage` inte används får vi fortfarande misalignment-problemet:

1. Bilden renderas med `object-fit: contain` inom `.receipt-modal-image-wrapper`
2. Om bilden är smalare/kortare än wrapper får vi letterboxing
3. Overlays beräknas från wrapper's top-left hörn, inte bildens
4. Resultat: Overlays är offset från rätt position

**Exempel:**
- Wrapper: 800px bred
- Bild: 600px bred (efter contain)
- Letterboxing: 100px på varje sida
- Overlay vid x=50% tror den är vid 400px men borde vara vid 300px (relativt bilden)
- Faktisk offset: 100px fel

### 2.3 Utvecklarupplevelse

CSS-klassen `.receipt-modal-image-stage` existerar men används aldrig → dead code
`imgRef` referens nämns i instruktioner men finns inte i kod → inkonsistens

---

## 3. Vad Fungerar Korrekt

### 3.1 ✅ Overlay Rendering
- Overlays renderas för varje box i `payload.boxes`
- Använder korrekt `toCss()` helper för att hantera både normalized (0-1) och pixel-värden
- Z-index layering fungerar (`highlighted` → z:3, normal → z:1, `muted` → z:0)

### 3.2 ✅ Styling System
- Yellow färgschema (253, 224, 71) konsekvent genom alla komponenter
- Transitions för smooth hover-effekter
- Dark theme integration

### 3.3 ✅ Data Flow
- `payload.boxes` hämtas korrekt från API
- `normaliseFieldId()` fungerar för att matcha field keys
- State management är solid

---

## 4. Vad Behöver Fixas

### 4.1 KRITISKT - Field Hover Handlers

**Prioritet:** HOOG
**Impact:** Hög - huvudfunktionaliteten saknas

**Åtgärd:**
Lägg till för **varje** field i alla sektioner:

```jsx
<div
  key={field.key}
  className={`receipt-modal-field ${matchHighlight(field.key)}`}
  onMouseEnter={() => setHoverField(field.key)}
  onMouseLeave={() => setHoverField(null)}
>
  {/* existing content */}
</div>
```

**Påverkade kodrader:**
- Rad ~908: Företagsinformation (9 fields)
- Rad ~944: Betalningstyp (12 fields)
- Rad ~978: Belopp (9 fields)
- Rad ~1084: Item cards och cells (variabelt antal)

**Estimerad arbetsinsats:** 30-45 minuter

### 4.2 KRITISKT - Image Stage Wrapper

**Prioritet:** HÖG
**Impact:** Hög - alignment accuracy

**Åtgärd:**
1. Lägg till `imgRef` konstant:
```jsx
const imgRef = React.useRef(null);
```

2. Wrappa bilden och overlays i stage:
```jsx
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
        /* overlays här - flytta från nuvarande position */
      })}
    </div>
  ) : (
    <div className="receipt-modal-image-fallback">Ingen bild</div>
  )}
</div>
```

**Påverkad kodrad:** Rad 1030-1064

**Estimerad arbetsinsats:** 15-20 minuter

### 4.3 MEDIUM - Item Row Hover

**Prioritet:** MEDIUM
**Impact:** Medium - förbättrar UX för radspecifika overlays

**Åtgärd:**
Om item-level boxes används (format: `items[0]`, `items[1]` etc):

```jsx
<div
  key={`item-${itemIndex}`}
  className={`receipt-item-card-new ${matchHighlight(`items[${itemIndex}]`)}`}
  onMouseEnter={() => setHoverField(`items[${itemIndex}]`)}
  onMouseLeave={() => setHoverField(null)}
>
  {/* existing content */}
</div>
```

**Påverkad kodrad:** Rad 1084

**Estimerad arbetsinsats:** 10 minuter

---

## 5. Testing Recommendations

Efter fixarna ska följande verifieras:

### 5.1 Visual Alignment Test
1. Öppna receipt med boxes
2. Kontrollera att overlays är exakt över rätt text i bilden
3. Testa med olika bildstorlekar (portrait, landscape, square)
4. Resize browser window → overlays ska följa bilden

### 5.2 Bidirectional Hover Test
1. Hover över overlay → både overlay OCH field ska bli gul
2. Hover över field → både field OCH overlay ska bli gul
3. Hover över field → andra overlays ska bli muted (opacity 0.35)
4. Lämna hover → allt ska återgå till normal state

### 5.3 Multi-Field Test
1. Hover snabbt mellan olika fields
2. Kontrollera att highlight uppdateras utan lag
3. Kontrollera att endast en field/overlay pair är highlighted åt gången

### 5.4 Edge Cases
1. Fields utan motsvarande box → highlight endast field
2. Boxes utan motsvarande field → highlight endast overlay
3. Tom boxes array → inga crashes
4. Många overlays (>50) → performance acceptable

---

## 6. Code Quality Observations

### 6.1 ✅ Bra Practices
- Konsekvent naming conventions
- God separation mellan helper functions och komponenter
- Mojibake-hantering för encoding issues
- Fallback-logik för missing data

### 6.2 ⚠️ Förbättringsområden
- Dead CSS code (`.receipt-modal-image-stage` definierad men oanvänd)
- Inkonsistens mellan instruktioner och implementation
- Saknar kommentarer kring varför stage inte används
- Inga TypeScript types (om det är önskat)

---

## 7. Slutsats och Rekommendationer

### 7.1 Slutsats
Task 5.4 är **inte fullt implementerad**. De fundamentala byggblocken finns (state, CSS, helpers) men **kritiska integrationspunkter saknas**:

1. ❌ Image stage wrapper används inte → alignment issues kvarstår
2. ❌ Field hover handlers saknas helt → main feature fungerar inte
3. ⚠️ Endast overlay→field highlight fungerar, inte field→overlay

### 7.2 Prioriterad Åtgärdsplan

**Phase 1 - Kritiska Fixar (45-60 min):**
1. Implementera image stage wrapper (20 min)
2. Lägg till field hover handlers i alla sektioner (40 min)

**Phase 2 - Testing (30 min):**
3. Verifiera alignment med olika bildstorlekar
4. Testa bidirectional hover i alla field-grupper
5. Edge case testing

**Phase 3 - Optional Enhancements:**
6. Item-level hover (10 min)
7. Performance optimization om >50 boxes
8. TypeScript types om önskat

### 7.3 Estimerad Total Tid
- **Minimum (kritiska fixes):** 1.5 timmar
- **Recommended (inkl. testing):** 2 timmar
- **Full (inkl. enhancements):** 2.5 timmar

### 7.4 Nästa Steg
1. ✅ Läs denna rapport
2. ⏭️ Bestäm om fixarna ska implementeras nu eller senare
3. ⏭️ Om nu: börja med Phase 1 enligt instruktionerna i Section 4
4. ⏭️ Om senare: skapa tasks i MIND_TASKS.md

---

## 8. Appendix - Filreferenser

**Analyserade filer:**
- `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx` (1268 rader)
- `main-system/app-frontend/src/index.css` (overlay styles rad 940-978)
- `docs/tasks/MIND_OVERLAY_ISSUES.md` (instruktioner)

**Kodrader som behöver uppdateras:**
- ReceiptPreviewModal.jsx: rad 633 (add imgRef), 908, 944, 978, 1030-1064, 1084

**Relaterade filer (ej ändrade):**
- `main-system/app-frontend/src/ui/pages/Receipts.jsx`
- `main-system/app-frontend/src/ui/pages/Process.jsx`
- `main-system/app-frontend/src/ui/pages/CompanyCard.jsx`

---

**Rapport Genererad:** 2025-10-19
**Version:** 1.0
**Status:** READY FOR REVIEW
