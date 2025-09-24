# MIND Ports Ledger (v2.0)

Active profiles and ports:
- Admin SPA (Nginx): 8008 → proxies to ai-api
- AI-API (Flask internal): 5000 (container), proxied via /ai/api
- MySQL: 3310 (host) → 3306 (container)
- Redis: 6380 (host) → 6379 (container)
- Prometheus: 9091 (host) → 9090 (container)
- Grafana: 3003 (host) → 3000 (container)

Deprecated in v2.0:
- PHP UI: 8004
- PHP API: 8009
- phpMyAdmin: 8087

Notes:
- Disable deprecated ports in active docker-compose profiles.
- Keep this file in sync with docker-compose.yml and technical plan.
