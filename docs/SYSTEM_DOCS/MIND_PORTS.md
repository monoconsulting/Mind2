# MIND — Project Port Ledger

**Authoritative note:** Host ports bind to `127.0.0.1` for local dev. Do **not** expose to LAN by default.
**Before assigning any ports:** consult the **Atlas** port registry and follow **@CHECK_PORTS_API.md**.

## Services & Ports (host → container)
> Values are based on `docker-compose.yml` as of 2025-09-23.

| Service                  | Host:Port (from .env) | Container:Port | Proto | Purpose / Notes                                  |
| ------------------------ | --------------------- | -------------- | ----- | ------------------------------------------------ |
| nginx                    | `8008`                | `80`           | HTTP  | Reverse Proxy for frontend and backend API       |
| mysql                    | `3310`                | `3306`         | TCP   | MySQL Database                                   |
| redis                    | `6380`                | `6379`         | TCP   | Celery message broker and cache                  |
| prometheus               | `9091`                | `9090`         | HTTP  | Metrics collection                               |
| grafana                  | `3003`                | `3000`         | HTTP  | Metrics visualization                            |
| ai-api                   | -                     | `5000`         | HTTP  | Internal API, accessed via Nginx                 |
| mind-web-main-frontend   | -                     | `80`           | HTTP  | Internal Frontend, accessed via Nginx            |

## Network Exposure & Firewall Rules
- The primary entry point is Nginx on port `8008`.
- Database and Redis ports are exposed to the host for development and debugging but should be firewalled in a production environment.
- `ai-api` and `mind-web-main-frontend` are not directly exposed to the host; all traffic is routed through Nginx.