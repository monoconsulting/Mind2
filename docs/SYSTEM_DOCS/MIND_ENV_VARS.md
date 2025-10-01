# MIND — Environment Variables

> Based on `.env.example` and `docker-compose.yml` as of 2025-09-23.

## `ai-api` & `celery-worker` Services

| Variable         | Required? | Default (in code/compose) | Example (`.env.example`) | Description                                                 |
| ---------------- | --------- | ------------------------- | ------------------------ | ----------------------------------------------------------- |
| `DB_HOST`        | Yes       | `mysql`                   | `127.0.0.1`              | Hostname for the MySQL database.                            |
| `DB_PORT`        | Yes       | `3306`                    | `3310`                   | Port for the MySQL database.                                |
| `DB_NAME`        | Yes       | -                         | `mono_se_db_9`           | The name of the database to use.                            |
| `DB_USER`        | Yes       | -                         | `mind`                   | Username for database authentication.                       |
| `DB_PASS`        | Yes       | -                         | `<set via secrets>`      | Password for database authentication.                       |
| `REDIS_HOST`     | Yes       | `redis`                   | `127.0.0.1`              | Hostname for the Redis server.                              |
| `REDIS_PORT`     | Yes       | `6379`                    | `6379`                   | Port for the Redis server.                                  |
| `JWT_SECRET_KEY` | Yes       | -                         | `<set via secrets>`      | Secret key for signing JWT tokens.                          |
| `ALLOWED_ORIGINS`| No        | -                         | `http://localhost:8008`  | Comma-separated list of allowed origins for CORS.           |
| `LOG_LEVEL`      | No        | `INFO`                    | `INFO`                   | The logging level (e.g., `INFO`, `DEBUG`).                  |
| `ADMIN_PASSWORD` | No        | -                         | `<set-for-dev-or-staging-only>` | Password for the admin user, for dev/staging.       |
| `STORAGE_DIR`    | No        | `/data/storage`           | -                        | Directory for storing uploaded files.                       |
| `FTP_LOCAL_DIR`  | No        | `/data/inbox`             | -                        | Local directory for the FTP fetcher service.                |
| `AI_PROCESSING_ENABLED` | No | -                         | `true`                   | Feature flag to enable or disable AI processing.            |

## `mysql` Service

| Variable              | Required? | Description                                           |
| --------------------- | --------- | ----------------------------------------------------- |
| `MYSQL_ROOT_PASSWORD` | Yes       | The root password for the MySQL instance.             |
| `MYSQL_DATABASE`      | Yes       | The name of the database to create on startup.        |
| `MYSQL_USER`          | Yes       | The name of the user to create on startup.            |
| `MYSQL_PASSWORD`      | Yes       | The password for the user to create on startup.       |