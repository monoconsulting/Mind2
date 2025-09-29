# Runbooks

## Mind API
- Start (dev): docker compose up (monitoring profile optional)
- Health: `/system/metrics` (Prometheus), container logs
- Common issues: Redis connectivity, MySQL migrations, import paths

## Celery Workers
- Start via docker compose (worker service)
- Queues: default; visibility timeout 1h
- Troubleshooting: check Redis, look for acks/retries

## Observability
- Prometheus port per `docs/MIND_PORTS.md`
- Grafana dashboards: API latency, task throughput
