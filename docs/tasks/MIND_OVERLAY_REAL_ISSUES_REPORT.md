# Overlay Real Issues Report - Rotation och Positioning

**Datum:** 2025-10-19
**Status:** 🟠 PROBLEM IDENTIFIERAT
**Test:** Video och manuell testning visar att overlays renderas men har problem

---

## KORRIGERAD PROBLEMANALYS

### Vad Som FAKTISKT Fungerar:
- ✅ Overlays renderas (gula boxar syns)
- ✅ Overlays byter färg vid hover
- ✅ API returnerar 26 boxes med korrekt data

### Vad Som INTE Fungerar:
- ❌ **Felroterade** - Overlays har fel rotation/orientation
- ❌ **Felpositionerade** - Overlays är inte på rätt plats på bilden
- ❌ **Hover matching** - Field-hover highlightar inte motsvarande overlay korrekt

---

## PROBLEM 1: ROTATION/ORIENTATION

### Symptom:
Overlays verkar vara roterade eller orienterade fel relativt bilden.

### Möjliga Orsaker:

#### A) Bildrotation Hanteras Inte
**Problem:**
- Kvittobilden kan ha EXIF orientation data
- Browsern roterar bilden automatiskt
- Men overlays följer inte rotationen

**Lösning:**
```jsx
// Läs EXIF orientation från bilden
const [imageOrientation, setImageOrientation] = React.useState(1);

React.useEffect(() => {
  if (imgRef.current && imgRef.current.complete) {
    // Läs EXIF data om möjligt
    // Eller detektera faktisk rendered rotation
    const img = imgRef.current;
    const naturalWidth = img.naturalWidth;
    const naturalHeight = img.naturalHeight;
    const displayWidth = img.width;
    const displayHeight = img.height;

    // Detektera om bilden är roterad
    const isRotated = (naturalWidth > naturalHeight) !== (displayWidth > displayHeight);
    setImageOrientation(isRotated ? 6 : 1); // 6 = 90° rotation
  }
}, [baseImageSrc]);

// Applicera rotation transform på overlays
const getOverlayStyle = (box) => {
  let style = {
    position: 'absolute',
    top: toCss(box.y ?? box.top ?? 0),
    left: toCss(box.x ?? box.left ?? 0),
    width: toCss(box.w ?? box.width ?? 0),
    height: toCss(box.h ?? box.height ?? 0),
  };

  // Om bild är roterad, rotera koordinater
  if (imageOrientation === 6) { // 90° rotation
    style = {
      ...style,
      top: toCss(box.x ?? box.left ?? 0),
      left: toCss(1 - (box.y ?? box.top ?? 0) - (box.h ?? box.height ?? 0)),
      width: toCss(box.h ?? box.height ?? 0),
      height: toCss(box.w ?? box.width ?? 0),
    };
  }

  return style;
};
```

#### B) Backend Koordinater Är För Fel Orientation
**Problem:**
- Backend genererar boxes för original bild (före rotation)
- Frontend visar roterad bild
- Koordinater matchar inte

**Verifiering:**
```bash
# Kolla bildens naturliga dimensioner
curl -s http://localhost:8008/ai/api/receipts/933b749c-d31e-46f8-b58f-4dfdfcdd74b6/image -o /tmp/receipt.jpg
identify /tmp/receipt.jpg  # Kolla dimensioner och EXIF
```

**Lösning:**
Backend bör returnera `orientation` i API response:
```json
{
  "boxes": [...],
  "image_metadata": {
    "orientation": 6,  // EXIF orientation
    "width": 2000,
    "height": 3000
  }
}
```

---

## PROBLEM 2: FELPOSITIONERING

### Symptom:
Overlays är offset från rätt position på bilden.

### Möjliga Orsaker:

#### A) Koordinatsystem Mismatch

**Backend använder:** Absoluta pixelkoordinater baserat på original bilddimensioner
**Frontend förväntar:** Normalized 0-1 koordinater

**Verifiering:**
```javascript
// I console när modal är öppen
console.log('First box:', boxes[0]);
// Om x > 1 → pixel coordinates
// Om x < 1 → normalized coordinates
```

**Från API data vi såg:**
```json
{
  "x": 0.6980820105820106,  // < 1 = normalized ✅
  "y": 0.5307539682539684,  // < 1 = normalized ✅
  "w": 0.016865079365079364, // < 1 = normalized ✅
  "h": 0.015873015873015872  // < 1 = normalized ✅
}
```

Så koordinater ÄR normalized. Men...

#### B) Image Stage Dimensions Fel

**Problem:**
`.receipt-modal-image-stage` kanske inte har exakt samma dimensioner som den renderade bilden.

**Debug:**
```jsx
React.useEffect(() => {
  if (imgRef.current) {
    const img = imgRef.current;
    const stage = img.parentElement;

    console.log('[DEBUG] Image dimensions:', {
      natural: { w: img.naturalWidth, h: img.naturalHeight },
      display: { w: img.width, h: img.height },
      client: { w: img.clientWidth, h: img.clientHeight },
      offset: { w: img.offsetWidth, h: img.offsetHeight }
    });

    console.log('[DEBUG] Stage dimensions:', {
      client: { w: stage.clientWidth, h: stage.clientHeight },
      offset: { w: stage.offsetWidth, h: stage.offsetHeight },
      scroll: { w: stage.scrollWidth, h: stage.scrollHeight }
    });

    // Stage MÅSTE matcha img display dimensions
    if (stage.clientWidth !== img.clientWidth || stage.clientHeight !== img.clientHeight) {
      console.error('[DEBUG] MISMATCH! Stage != Image dimensions');
    }
  }
}, [baseImageSrc, payload]);
```

**Möjlig Fix:**
```css
.receipt-modal-image-stage {
  position: relative;
  display: inline-block;
  line-height: 0;
  /* VIKTIGT: Inga padding, margin eller border */
  padding: 0;
  margin: 0;
  border: 0;
}

.receipt-modal-image {
  display: block; /* Viktigt för att undvika inline spacing */
  /* Inga margin/padding här heller */
  margin: 0;
  padding: 0;
}
```

#### C) Aspect Ratio Distortion

**Problem:**
Om bilden skalas med olika aspect ratio än original, blir koordinaterna fel.

**Verifiering:**
```javascript
const img = imgRef.current;
const aspectRatioOriginal = img.naturalWidth / img.naturalHeight;
const aspectRatioDisplay = img.width / img.height;
console.log('Aspect ratio match:', Math.abs(aspectRatioOriginal - aspectRatioDisplay) < 0.01);
```

---

## PROBLEM 3: HOVER MATCHING

### Symptom:
När man hovrar över ett field highlightas fel overlay (eller ingen overlay).

### Möjliga Orsaker:

#### A) Field Key Mismatch

**Problem:**
`box.field` från API matchar inte `field.key` i UI.

**Från API data:**
```json
{
  "field": "SE",  // ← Mycket kort field name
  "x": 0.698,
  ...
}
```

**Från UI kod:**
Vi använder keys som:
- `name`, `orgnr`, `address`, `purchase_datetime`, `gross_amount` etc.

**KRITISKT: `"SE"` matchar inte någon av dessa!**

**Verifiering:**
```jsx
// Lägg till debug i matchHighlight
const matchHighlight = (key) => {
  if (!hoverField || !key) {
    return '';
  }
  const normalized1 = normaliseFieldId(hoverField);
  const normalized2 = normaliseFieldId(key);
  const isMatch = normalized1 === normalized2;

  console.log('[MATCH]', {
    hoverField,
    key,
    normalized1,
    normalized2,
    isMatch
  });

  return isMatch ? 'highlighted' : 'muted';
};
```

#### B) Backend Använder Fel Field Names

**Problem:**
Backend genererar `box.field` som inte motsvarar frontend field keys.

**Från API exempel:**
- `"SE"` - Vad betyder detta? Sverige?
- `"MS"` - ?
- `"Handelsban"` - Troligen "Handelsbanken" (företagsnamn)
- `"30308472"` - Troligen org.nr
- `"2025-09-08 08:40"` - Datum/tid

**Backend verkar använda det EXTRAHERADE VÄRDET som field name istället för field TYPE!**

**Detta är FUNDAMENTALT FEL!**

**Förväntat:**
```json
{
  "field": "receipt.merchant_name",  // eller "company.name"
  "value": "Handelsbanken",
  "x": 0.7,
  ...
}
```

**Faktiskt:**
```json
{
  "field": "Handelsban",  // Värdet, inte field-typen!
  "x": 0.7,
  ...
}
```

---

## ROOT CAUSE IDENTIFIED

**HUVUDPROBLEMET:** Backend `box.field` innehåller extraherat TEXT CONTENT istället för FIELD IDENTIFIER.

Detta förklarar:
1. ✅ Varför overlays renderas (data finns)
2. ✅ Varför de byter färg (hover fungerar på overlays)
3. ❌ Varför field→overlay matching inte fungerar (field names matchar inte)

### Exempel från Data:

**API boxes:**
```json
[
  {"field": "SE", "x": 0.698, "y": 0.530, ...},
  {"field": "MS", "x": 0.704, "y": 0.619, ...},
  {"field": "Handelsban", "x": 0.700, "y": 0.549, ...},
  {"field": "30308472", "x": 0.715, "y": 0.525, ...}
]
```

**Frontend fields:**
```javascript
{key: 'name', label: 'Företag'}  // Värde: "BAUHAUS"
{key: 'orgnr', label: 'Organisationsnummer'}  // Värde: "969630-6944"
{key: 'purchase_datetime', label: 'Inköpsdatum'}  // Värde: "2025-09-08"
```

**Ingen match mellan "SE" och "name"!**

---

## LÖSNINGSFÖRSLAG

### Lösning A: Backend Fix (REKOMMENDERAD)

**Backend måste ändra box generation för att använda semantic field names:**

```python
# FÖRE (FEL):
boxes = [
    {
        "field": extracted_text,  # "Handelsbanken"
        "x": 0.7,
        ...
    }
]

# EFTER (RÄTT):
boxes = [
    {
        "field": "company.name",  # Semantic identifier
        "value": "Handelsbanken",  # Extraherad text
        "confidence": 0.99,
        "x": 0.7,
        ...
    }
]
```

**Mapping som behövs:**
```python
# Backend AI som identifierar field types
text_to_field_mapping = {
    # Identifiera baserat på position, kontext, OCR confidence
    "Handelsbanken": "company.name",
    "969630-6944": "company.orgnr",
    "2025-09-08": "receipt.purchase_date",
    "359.00": "receipt.gross_amount",
    # etc.
}
```

---

### Lösning B: Frontend Fuzzy Matching (WORKAROUND)

**Om backend inte kan fixas snabbt, implementera fuzzy matching:**

```javascript
function findMatchingBox(fieldKey, fieldValue, boxes) {
  // Försök exakt field match först
  let match = boxes.find(box =>
    normaliseFieldId(box.field) === normaliseFieldId(fieldKey)
  );

  if (match) return match;

  // Fuzzy match på värde
  if (fieldValue && typeof fieldValue === 'string') {
    match = boxes.find(box => {
      const boxField = box.field?.toString().toLowerCase();
      const value = fieldValue.toString().toLowerCase();

      // Partial match
      return boxField?.includes(value) || value.includes(boxField);
    });
  }

  return match;
}

// Användning i field render:
const hoverKey = (() => {
  const fieldValue = sourceData[field.key];
  const matchedBox = findMatchingBox(field.key, fieldValue, boxes);
  return matchedBox?.field || field.key;
})();
```

---

### Lösning C: Hybrid Approach

**Använd både semantic och fuzzy matching:**

```javascript
// buildHoverCandidates inkluderar också värdet
const hoverCandidates = [
  field.key,  // 'name'
  `company.${field.key}`,  // 'company.name'
  `receipt.${field.key}`,  // 'receipt.name'
  sourceData[field.key],  // 'BAUHAUS' (faktiska värdet)
  sourceData[field.key]?.substring(0, 10),  // 'BAUHAUS' truncated
];

// resolveBoxField hittar första matchningen
const matchedBox = boxes.find(box => {
  const normalized = normaliseFieldId(box.field);
  return hoverCandidates.some(candidate =>
    normaliseFieldId(candidate) === normalized
  );
});
```

---

## ROTATION PROBLEM - SPECIFIK LÖSNING

### Detektera och Hantera Bildrotation

```jsx
const [imageTransform, setImageTransform] = React.useState({
  rotation: 0,
  scaleX: 1,
  scaleY: 1
});

React.useEffect(() => {
  if (!imgRef.current) return;

  const img = imgRef.current;
  const computedStyle = window.getComputedStyle(img);
  const transform = computedStyle.transform;

  // Detektera rotation från transform matrix
  if (transform && transform !== 'none') {
    const values = transform.split('(')[1].split(')')[0].split(',');
    const a = values[0];
    const b = values[1];
    const angle = Math.round(Math.atan2(b, a) * (180 / Math.PI));

    setImageTransform({
      rotation: angle,
      scaleX: parseFloat(values[0]),
      scaleY: parseFloat(values[3])
    });
  }

  // Eller läs EXIF orientation
  // ... EXIF reading logic
}, [baseImageSrc]);

// Transformera overlay koordinater
const transformCoordinates = (box, transform) => {
  let {x, y, w, h} = box;

  switch(transform.rotation) {
    case 90:
      return {
        x: 1 - y - h,
        y: x,
        w: h,
        h: w
      };
    case 180:
      return {
        x: 1 - x - w,
        y: 1 - y - h,
        w,
        h
      };
    case 270:
      return {
        x: y,
        y: 1 - x - w,
        w: h,
        h: w
      };
    default:
      return {x, y, w, h};
  }
};

// Användning:
{boxes.map((box, index) => {
  const transformed = transformCoordinates(box, imageTransform);
  return (
    <div
      className="receipt-modal-overlay"
      style={{
        top: toCss(transformed.y),
        left: toCss(transformed.x),
        width: toCss(transformed.w),
        height: toCss(transformed.h),
      }}
    />
  );
})}
```

---

## IMMEDIATE ACTION PLAN

### STEG 1: Verifiera Field Name Problem (5 min)

```javascript
// I console när modal är öppen:
console.log('Boxes field names:', boxes.map(b => b.field));
console.log('Frontend field keys:', [
  'name', 'orgnr', 'address', 'purchase_datetime', 'gross_amount'
  // ... alla field keys
]);
// Jämför - matchar någon?
```

### STEG 2: Test Fuzzy Matching (30 min)

Implementera Lösning B (fuzzy matching) som quick fix.

### STEG 3: Backend Discussion (TBD)

Diskutera med backend team att fixa `box.field` till semantic names.

### STEG 4: Rotation Detection (45 min)

Implementera rotation detection och coordinate transformation.

---

## EXPECTED RESULTS EFTER FIX

### När Field Matching Fungerar:
- ✅ Hover över "Företag: BAUHAUS" → overlay över "BAUHAUS" i bilden blir gul
- ✅ Hover över overlay i bilden → motsvarande field blir gul
- ✅ Andra overlays blir muted (transparent)

### När Rotation Fungerar:
- ✅ Overlays placeras korrekt även på roterade bilder
- ✅ Portrait och landscape bilder båda fungerar

### När Positioning Fungerar:
- ✅ Overlays är exakt över rätt text i bilden
- ✅ Ingen offset horisontellt eller vertikalt
- ✅ Resize window → overlays följer bilden

---

## SLUTSATS

**Problem identifierat:**
1. Backend `box.field` innehåller text content istället för field identifiers
2. Möjlig bildrotation hanteras inte
3. Koordinattransformation kan behövas för roterade bilder

**Lösning:**
1. **Short-term:** Fuzzy matching baserat på text content
2. **Long-term:** Backend fix för semantic field names
3. **Rotation:** Detektera och transformera koordinater

**Kod är korrekt implementerad** - problemet är data-format och rotation handling.

---

**Report Created:** 2025-10-19
**Status:** 🟠 ROOT CAUSE IDENTIFIED
**Next Steps:** Implementera fuzzy matching + rotation handling
