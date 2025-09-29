# XXXX — Frontend Architecture & Implementation  
```
File: XXXX_FRONTEND_v.0.1.md  
Version: 0.1  
```

---

## Changelog

| Date       | Filename               | Version | Changes                                                      | Author       |
| ---------- | ---------------------- | ------- | ------------------------------------------------------------ | ------------ |
| 2025-09-21 | XXXX_FRONTEND_v.0.1.md | 0.1     | Added updated security, performance, compatibility, privacy questions | Agent (name) |

---

## Purpose

This document describes **how the frontend is structured, implemented, integrated, and secured**, including recent best practices as of 2025-09-21. No guessing allowed: all statements must be supported by code references (file names / lines).

---

## 1. High-Level Overview

- Framework / Library  
  - Which framework/library is used (React, Vue, etc.)  
  - Exact version(s), verify from `package.json` and `lock` files (yarn.lock / package-lock.json)  
- Build & Toolchain  
  - Which bundler/build tool (Vite, Webpack, Rollup, etc.)  
  - All `package.json` scripts (dev, build, lint, test, preview etc.)  
  - Transpilation targets (browserslist / TypeScript target etc.)  
- Styling & Design System  
  - Styling solution (Tailwind, SCSS, CSS-in-JS etc.)  
  - Design tokens / theme files (colors, typography, spacing etc.)  
- Routing & Navigation  
  - Router used, route definitions  
  - SSR, CSR, or hybrid per route  
  - Lazy-loading / code splitting  

---

## 2. Component Inventory

| Component        | Path                 | Props / Inputs             | Outputs / Events     | Responsibility / Purpose               |
| ---------------- | -------------------- | -------------------------- | -------------------- | -------------------------------------- |
| ExampleComponent | `src/components/...` | `propA: string`, `onClick` | `onClick()` callback | Description of what the component does |

- Include screenshots of key views (desktop & mobile).  
- Identify reused components vs page-specific.  
- Mark server- vs client-rendered components.  

---

## 3. API & Backend Integration

- HTTP client / data fetching library used (axios / fetch / custom wrapper etc.)  
- Interceptors (auth, logging, error handling)  
- All API endpoints in use: GET / POST / PATCH / DELETE. Link to backend spec.  
- Location of base URL / configs (env files etc.)  

---

## 4. Authentication, Security & Privacy

- Authentication mechanism: JWT / OAuth / session cookie etc.  
- Storage of tokens: localStorage / sessionStorage / cookies / other.  
- Route protection / protected pages.  
- Hardcoded secrets/endpoints in code?  
- Security policies: CSP, CORS, Cross-Site scripting (XSS) defenses, CSRF protections.  
- Dependency security: any vulnerable packages? Is a dependency audit in place?  
- Privacy / data protection: handling of user personal data, GDPR compliance etc.  

---

## 5. Performance, Compatibility & Optimization

- Lazy loading / code splitting in routes / components  
- Image/font optimization (formats, compression)  
- Web Vitals: LCP, FID, CLS etc. Do we measure them?  
- Browser support: target browsers, polyfills, fallback strategies.  
- Caching strategies (static assets, service workers if any)  

---

## 6. Testing, Quality Assurance & Accessibility

- Unit tests, integration tests, E2E tests. Frameworks used.  
- Linting, formatting rules (ESLint, Prettier)  
- Accessibility: WCAG 2.1/2.2 compliance. Contrast, keyboard nav, ARIA usage, screen reader tests.  
- Internationalization / localization: support for multiple languages, hardcoded text etc.

---

## 7. DevOps & Environment Setup

- List all `.env` variables frontend requires (development, staging, prod)  
- Build and deploy pipelines: CI/CD scripts, preview builds etc.  
- Instructions to run locally: install, build, test, preview.  

---

## 8. Mandatory Review Questions

Agents **must provide** clear answers with code/file references:

1. Are there **hardcoded endpoints** or secrets in code instead of being in configuration/env?  
2. Are there **unused components, CSS, assets, or styles** that can be removed?  
3. Are there any **duplicated code** (functions, logic, styles) that deserve refactoring?  
4. What are the **security risks** present (e.g. XSS, CSRF, insecure storage, lack of CSP)?  
5. Are there **performance issues** (bundle size too large, images/fonts unoptimized, missing code splitting)?  
6. Are there **accessibility issues** (missing alt attributes, low contrast, missing keyboard navigation, ARIA)?  
7. Are there gaps in **browser compatibility or transpilation** (e.g. missing polyfills)?  
8. Are there **dependency vulnerabilities** (known CVEs)? Is there a process for audits?  
9. Any privacy / data protection concerns (collecting personal data unnecessarily, sending data insecurely etc.)?  
10. Does any part of the code log sensitive information or leave debug code in production?  

---

## Validation Checklist

- [ ] Replaced all `XXXX` with actual project name  
- [ ] Framework/library versions verified from `package.json` / lock files  
- [ ] Component inventory is full and accurate  
- [ ] API endpoints cross-checked with backend spec  
- [ ] Security & privacy sections answered with code refs  
- [ ] Performance and compatibility issues identified  
- [ ] Accessibility checks done  
- [ ] Tests, linting, i18n documented  
- [ ] Local dev + deploy instructions complete  

---