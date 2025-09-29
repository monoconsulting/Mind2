# Security Hardening Checklist (Initial)

- Static analysis:
  - pre-commit: flake8, isort, black, bandit (added)
- Dependency audit:
  - Python: `pip-audit` (run locally or in CI)
  - Node: `npm audit` (frontend)
- Secrets scanning:
  - Recommend `gitleaks` or GitHub Advanced Security (if available)
- Config:
  - Use `JWT_SECRET` from environment in production; rotate periodically
  - Restrict CORS origins via `ALLOWED_ORIGINS`
- Runtime:
  - Minimal privileges for containers; avoid running as root
  - Network policies: only expose necessary ports (see MIND_PORTS)
