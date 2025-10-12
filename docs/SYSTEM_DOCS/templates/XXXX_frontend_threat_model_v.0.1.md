# XXXX — Frontend Threat Model & Risk Register
File: XXXX_FRONTEND_THREAT_MODEL_v.0.1.md  
Version: 0.1

---

## Changelog

| Date       | Filename                               | Version | Changes made                                  | Author        |
|------------|----------------------------------------|---------|-----------------------------------------------|---------------|
| 2025-09-21 | XXXX_FRONTEND_THREAT_MODEL_v.0.1.md    | 0.1     | Initial threat model & risk register template | Agent (name)  |

---

## Purpose

This document provides a **deep, code-anchored threat model** for the frontend and a living **risk register**.  
It complements `XXXX_SECURITY.md` by forcing a systematic analysis of attack surfaces, mitigations, and evidence in code. **No guessing allowed** — reference files and line numbers.

---

## 1) System Context & Assets

- **Entry points** (routes, forms, URL params, message/event handlers, WebSocket endpoints).  
- **Data assets** handled in the frontend (auth tokens, profile data, PII).  
- **Trust boundaries** (browser ↔ backend API ↔ third‑party scripts/CDNs).  
- **Assumptions** explicitly listed and validated with code/infra references.

---

## 2) Threat Enumeration (STRIDE + Frontend specifics)

For each category, list **where** the risk exists, **how** it could be exploited, and **what** mitigation exists or is required.

### S — Spoofing
- Login flows, session fixation, OAuth redirect URIs, PKCE usage, token audience checks.

### T — Tampering
- Client‑side state tampering, query string overrides, feature flags in localStorage, integrity of cached assets.

### R — Repudiation
- Client event logging, auditability of privileged actions, correlation IDs.

### I — Information Disclosure
- Leaking tokens in URLs, Referer headers, console logs, error pages, stack traces, source maps in prod.

### D — Denial of Service
- Overly heavy pages, unthrottled requests, infinite loops, massive images, expensive client rendering.

### E — Elevation of Privilege
- Missing route guards, UI‑only access control, hidden buttons instead of true authorization.

### Frontend‑Specific
- **XSS** (DOM, reflected, stored; unsafe `dangerouslySetInnerHTML`, unsanitized HTML),  
- **CSRF** (cookie‑based auth without CSRF tokens / SameSite),  
- **Clickjacking** (missing `X-Frame-Options`/CSP `frame-ancestors`),  
- **Open Redirects** (`next=`/`redirect=` params),  
- **Third‑party scripts** (CSP, Subresource Integrity),  
- **Service Worker** risks (cache poisoning, offline auth),  
- **CORS** misconfigurations impacting frontend expectations.

---

## 3) Mitigations & Security Controls (with evidence)

- **CSP**: provide current policy; ensure `script-src`, `style-src`, `frame-ancestors`.  
- **Escaping/Sanitization**: libraries/utilities used; lint rules.  
- **AuthN/Z**: storage of tokens, refresh flows, route guards, server‑side authorization enforced.  
- **CSRF**: SameSite cookies, anti‑CSRF tokens, double‑submit.  
- **Dependencies**: audit process (npm audit/OWASP Dependency‑Check/Snyk/Dependabot).  
- **Build/Release**: source maps handling, minification, tree‑shaking, dead‑code elimination.  
- **Logging**: PII redaction, no tokens in logs, client error reporting policy.  
- **i18n/a11y**: text externalization, WCAG checks, automated a11y tests.

> For each control, **link to code/config** (paths + lines) and **paste current config** where appropriate.

---

## 4) Risk Register

| ID | Risk (What could go wrong?) | Likelihood | Impact | Risk Score | Current Controls | Needed Actions | Owner | Due Date | Status |
|----|------------------------------|------------|--------|------------|------------------|----------------|-------|---------|--------|
| FM‑001 | DOM‑XSS via unsanitized HTML in `ComponentX` | Medium | High | H | React escape by default; sanitizer missing | Add DOMPurify wrapper, unit test | Name | YYYY‑MM‑DD | Open |

> Use H/M/L scales or 1‑5; define your rubric in the appendix.

---

## 5) Mandatory Review Questions (Security Deep‑Dive)

1. **XSS**: Identify all places where HTML is injected or rendered from user/remote inputs. How is it sanitized/escaped? (files/lines)  
2. **CSRF**: If cookies are used, how is CSRF prevented? Provide evidence (code/config).  
3. **CSP**: What is the effective policy in production? Provide the exact header/meta.  
4. **Tokens**: Where are tokens stored (cookie/local/session/memory)? Rotation/expiry?  
5. **Open Redirects**: Are redirect params validated against an allow‑list? Where?  
6. **Third‑Party Scripts**: Which domains are allowed? Is SRI used?  
7. **Error/Logging**: Could errors/logs expose PII, tokens, or internals? Show sanitization.  
8. **Dependencies**: Latest audit results (tool, date, findings, remediation plan).  
9. **Source Maps**: Are production maps exposed? If yes, why?  
10. **Service Worker**: Is there a SW? What’s cached? Any auth leakage risks?  
11. **Authorization**: Are privileged UI paths guarded only in UI, or also server‑side? Evidence.  
12. **CORS**: Is CORS policy aligned with frontend origins? Misconfig risks?

---

## 6) Validation Checklist

- [ ] Threats enumerated and mapped to code.  
- [ ] Mitigations documented with concrete configs.  
- [ ] Risk register created with owners and due dates.  
- [ ] Latest dependency audit attached.  
- [ ] Findings cross‑referenced with `XXXX_SECURITY.md`, `XXXX_ENDPOINTS.md`, and `.env(.example)`.  

---

## Appendix

- **Risk Scoring Rubric** (define H/M/L or numeric scale).  
- **Glossary** (CSP, SRI, CSRF, XSS, etc.).  
- **References** (internal policies, OWASP ASVS/Top10‑2021+, WCAG 2.2).

