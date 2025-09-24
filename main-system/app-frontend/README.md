# Mind Admin Frontend (minimal)

Minimal Vite scaffold to preview the Admin SPA and integrate Darkmind design assets.

## Dev

Run dev server (requires Node LTS):

```
npm install
npm run dev
```

Vite dev server proxies `/ai/api` to `http://localhost:8008` (see `vite.config.js`).

## How to run and verify Receipts view

Prereqs:
- Backend is running and reachable on http://localhost:8008 with `/ai/api/auth/login` and `/ai/api/receipts` available
- `.env` has valid `ADMIN_PASSWORD` and `JWT_SECRET_KEY`

Steps:
1) Start the frontend dev server:
   - `npm run dev` and open the shown URL (default http://localhost:5173)
2) Log in:
   - Username: `admin`
   - Password: set in backend `.env` (`ADMIN_PASSWORD`)
3) Navigate to Receipts (top nav) and use filters:
   - Status, merchant, orgnr, date range
   - Pagination controls and page size
4) Verify behavior:
   - Data loads and shows total/page info
   - 401 responses auto-redirect to Login (token cleared)
   - Query params reflect filters (checked via devtools Network tab)

Troubleshooting:
- If login fails, check backend logs and ensure CORS/Proxy is correct
- On Windows PowerShell, when testing login via CLI, prefer `Invoke-RestMethod` with explicit JSON body:
  ```powershell
  $body = @{ username='admin'; password='YOUR_PASSWORD' } | ConvertTo-Json
  Invoke-RestMethod -Uri 'http://localhost:8008/ai/api/auth/login' -Method POST -Body $body -ContentType 'application/json'
  ```

## Integrate Darkmind Design

See `../ui-design/MIND_DESIGN_GUIDES.md` for full instructions.

Step-by-step (summary):
1) Obtain the Darkmind design package (e.g., `darkmind_design.zip`) and extract it.
2) In the extracted design package directory:
   - Install deps: `npm install`
   - Build assets: `npm run build` (outputs to `dist/`)
3) In this `frontend/` project:
   - Option A (recommended): Copy `dist/styles.css` → `public/darkmind.css`, and `dist/main.js` → `public/darkmind.js`
   - Option B: Replace `/src/styles.css` with the built `styles.css` and import the JS in `index.html`
4) Update `index.html`:
   ```html
   <link rel="stylesheet" href="/darkmind.css">
   <script src="/darkmind.js" defer></script>
   ```
   Ensure `<body>` has the required global classes (e.g., `dm-body`).
5) Verify:
   - Dark theme matches mockups
   - Responsive layouts across breakpoints
   - Fonts, icons, spacing are consistent
   - Interactive components behave as expected

This scaffold already points to `/darkmind.css` (in `public/`). Replace it with the real Darkmind build when available.
