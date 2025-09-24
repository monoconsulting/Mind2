# Secrets Runbook

This project uses environment variables for secrets (dev) and should use a secrets manager in non-dev.

- JWT_SECRET_KEY: HS256 signing key for admin JWTs
- ADMIN_PASSWORD: password for /auth/login

Dev/local:
- Use `.env` in repo root and docker compose to inject variables.
- Never commit real secrets.

Non-dev:
- Inject via orchestrator (Kubernetes secrets, Docker swarm secrets, or CI/CD environment).
- Do not bake secrets into images.

Rotation:
- Change secrets in the platform and restart services.
- Existing tokens will remain valid until expiry; shorten exp to accelerate rotation.
