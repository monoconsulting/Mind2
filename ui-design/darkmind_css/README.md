# DarkMind – React + Tailwind Dashboard

DarkMind is a dark, gradient-rich dashboard starter built with **React + Vite + Tailwind CSS**.
It bundles **local fonts**, **600+ icons (via react-icons/Feather and friends)**, and **interactive charts** (Chart.js).

## Quick Start

```bash
# 1) Extract the zip
cd DarkMind

# 2) Install deps (downloads fonts/icons locally via npm packages)
npm install

# 3) Start dev server
npm run dev

# 4) Build production
npm run build
npm run preview
```

> No external CDNs are used. Fonts and icons are installed locally via npm packages and bundled in your build.

## Tech

- React 18 + Vite 5
- Tailwind CSS 3 (utility classes; theme extended in `tailwind.config.js`)
- Charts: Chart.js + react-chartjs-2
- Icons: react-icons (Feather + others) – import only what you need
- Fonts: `@fontsource/inter` (local files, no Google Fonts CDN)

## Structure

```
DarkMind/
  public/
  src/
    assets/
    components/
      charts/
    data/
    pages/
    styles/
    App.jsx
    index.css
    main.jsx
  index.html
  package.json
  tailwind.config.js
  postcss.config.js
  vite.config.js
```

## Theming

- Colors defined under `dm.*` in `tailwind.config.js` and CSS vars in `src/index.css`.
- Change the accent gradient by tweaking `--dm-primary` & `--dm-primary2` in `index.css`.
- Font family is Inter (variable). Adjust in `tailwind.config.js` (`theme.extend.fontFamily.sans`).

## Icons

Use icons via `react-icons` (Feather subset shown below):

```jsx
import { FiHome, FiSettings } from 'react-icons/fi'

<FiHome className="text-xl" />
<FiSettings className="text-xl" />
```

## Charts

See `src/components/charts/LineAreaChart.jsx` and `DoughnutChart.jsx`. Replace demo data in `src/data/demo.js` with your own or fetch from an API.

## Routing

`react-router-dom` provides three example pages:

- `/` → Dashboard
- `/projects`
- `/analytics`

## License

MIT for this template. Icons and fonts under their respective OSS licenses.
