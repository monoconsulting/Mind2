# Screenshot SoT — Deterministic Visual Verification (NON-NEGOTIABLE)

**Audience:** Dev Agent  
**Purpose:** Produce screenshots that are *comparable across tasks* (pixel-level), so “visual parity” is provable.

This is mandatory for every task that claims “visual parity confirmed”.

---

## 1) Golden rules

### 1.1 Always capture the same state
Before every screenshot:
- **Scroll position must be TOP (0)** unless explicitly stated otherwise.
- **No hover states** (move mouse away from interactive elements).
- **No open dropdowns/menus/modals**.
- **No focused inputs**.
- **Same selected tab** (Overview vs Performance).
- **Same sidebar state**:
  - Default: **sidebar OPEN** (unless a task is about sidebar behavior; then capture both).

### 1.2 Always capture the same viewport
Use ONE standard viewport for all screenshots:
- **Viewport:** `1440 x 900` (width x height)
- **Device scale factor:** `1`
- **Headless:** OK
- **Color scheme:** light (default)

### 1.3 Always capture the same routes / entry
- Use the normal runtime entry (`npm run dev`) unless the task explicitly requires production build.
- Use the app’s built-in view switching (tabs) to navigate to Overview/Performance.

### 1.4 File naming is fixed
All screenshots must be written exactly here:
- `docs/facit/`

And named exactly:
- `dashboard_overview_after_taskX.png`
- `dashboard_performance_after_taskX.png`

Where `taskX` is the task number.  
Example: `dashboard_overview_after_task10.png`

---

## 2) How to capture manually (allowed but strict)

Manual capture is allowed only if you follow these steps exactly:

### 2.1 Browser setup (must)
- Use Chromium-based browser (Chrome/Edge).
- Open DevTools → toggle device toolbar OFF.
  - Set window size to exactly **1900x1200**.

- Zoom level: **100%**.
- Ensure OS scaling does not change between tasks.

### 2.2 App state setup

For Overview screenshot:
1) Start `npm run dev`
2) Open the app (default page)
3) Switch to **Overview** tab (if not already)
4) Ensure sidebar is **OPEN**
5) Scroll to **TOP**
6) Move mouse to empty background (no hover)
7) Take screenshot and save as:
   - `docs/facit/dashboard_overview_after_taskX.png`

For Performance screenshot:
1) Switch to **Performance**
2) Ensure sidebar is **OPEN**
3) Scroll to **TOP**
4) Move mouse away
5) Save as:
   - `docs/facit/dashboard_performance_after_taskX.png`

### 2.3 Manual proof requirement
When manual screenshots are used, the task verification report must include:
- The viewport used (must state `1900x1200`)
- Confirmation that scroll=top and sidebar=open
- Confirmation that no hover states were active

---

## 3) Preferred: Automated screenshots with Playwright (recommended)

### 3.1 Install Playwright once (repo-local)
Run:
- `npm i -D @playwright/test`
- `npx playwright install --with-deps chromium`

### 3.2 Add deterministic screenshot script
Create file:
- `scripts/facit-screenshots.mjs`

**Requirements for the script:**
- Launch Chromium
- Set viewport: `1900x1200`, `deviceScaleFactor: 1`
- Navigate to dev server URL 
- Ensure sidebar OPEN (click hamburger if needed; must detect state)
- Click Overview tab → scroll to top → screenshot
- Click Performance tab → scroll to top → screenshot
- Save to `docs/facit/`

### 3.3 Run command (every task)
- Start dev server: `npm run dev`
- In a second terminal:
  - `node scripts/facit-screenshots.mjs --task=10`

This must generate:
- `docs/facit/dashboard_overview_after_task10.png`
- `docs/facit/dashboard_performance_after_task10.png`

### 3.4 Automation proof requirement
The task report must include:
- The exact command used (including task number)
- Confirmation that the two files were generated
- `git status --short` showing the images changed

---

## 4) Mandatory consistency checks (every task)
Before claiming “visual parity confirmed”, do the following:

### 4.1 Binary file existence
Confirm both files exist:
- `docs/facit/dashboard_overview_after_taskX.png`
- `docs/facit/dashboard_performance_after_taskX.png`

### 4.2 Side-by-side sanity
Open the previous task screenshot and current screenshot side-by-side:
- Example: Task 9 vs Task 10
- Confirm:
  - Same viewport
  - Same scroll position
  - Same sidebar state
  - Same tab selection

### 4.3 If mismatch is found
If screenshots are not comparable (different scroll / different tab / different viewport):
- Re-take screenshots immediately.
- Do not claim “parity confirmed”.

---

## 5) Acceptance criteria for any task
A task is considered verified only if:
- `npm run build` succeeds
- Manual checks pass
- Screenshots are present in the repo AND included in the shared zip
- Screenshots are comparable to previous task (same viewport + same state)

---

## 6) Default settings (unless overridden by a specific task)
- Sidebar: **OPEN**
- Scroll: **TOP**
- Viewport: **1900x1200**
- Overview + Performance screenshots always taken

---