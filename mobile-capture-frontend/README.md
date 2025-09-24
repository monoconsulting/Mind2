# Mobile Receipt Capture Frontend

A mobile-optimized web application for capturing receipt photos, designed for deployment to public web hosting (e.g., `mind.mono.se`).

## Features

- **Mobile-first design** optimized for touch devices
- **Camera capture** with environment-facing camera preference
- **Gallery selection** for existing photos
- **Multi-page receipts** support (add multiple pages to single submission)
- **Tag selection** from predefined categories
- **Location opt-in** with simple Yes/No choice
- **Offline-capable** with service worker (future enhancement)

## User Flow

Based on `MIND_FUNCTION_DESCRIPTION.md`:

1. **Main Screen**: Take Photo or Gallery buttons
2. **Capture Flow**: Take photo → "Use this photo?" → Re-take/Add Page/Finished
3. **Tagging**: Select relevant tags from predefined list
4. **Location**: Simple "Add location data?" → Yes/No
5. **Submission**: Upload images + metadata to `/ai/api/capture/upload`
6. **Success**: Confirmation with option to submit another

## API Integration

Submits to MIND v2.0 backend:
- **Endpoint**: `POST /ai/api/capture/upload`
- **Format**: `multipart/form-data`
- **Fields**:
  - `images`: Multiple image files (page-1.jpg, page-2.jpg, ...)
  - `tags`: JSON array of selected tags
  - `location`: JSON object with lat/lon/accuracy (optional)

## Deployment

This is a **static web application** that can be deployed to:
- Static hosting (Netlify, Vercel, GitHub Pages)
- Web hotel/shared hosting
- CDN with index.html entry point

### Requirements
- Serves over HTTPS (required for camera access)
- Points API calls to MIND backend via `/ai/api/` proxy

### Configuration
Update API endpoint in `app.js` if backend is not available via `/ai/api/`:
```javascript
const response = await fetch('https://your-backend.com/ai/api/capture/upload', {
```

## Architecture

Per MIND_TECHNICAL_PLAN_v2.0.md:
- **Separate from admin SPA** (mind-web-main-frontend)
- **Public-facing** for external users
- **Mobile-optimized** for receipt capture only
- **No admin functionality** (Dashboard, Settings, etc.)

## Browser Support

- Modern mobile browsers (iOS Safari, Chrome, Firefox)
- Requires camera API support
- Graceful fallback to gallery-only if camera unavailable

## Development

```bash
# Serve locally
python -m http.server 8080
# or
npx serve .

# Access at http://localhost:8080
```

## Security Notes

- No authentication required (public capture)
- Validates file types client-side
- Server-side validation handled by backend
- CORS configured on backend for public access