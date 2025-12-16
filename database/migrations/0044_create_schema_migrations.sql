-- 0044_create_schema_migrations.sql
-- Purpose: Migration ledger to prevent replay of database/migrations/*.sql

CREATE TABLE IF NOT EXISTS schema_migrations (
  filename VARCHAR(255) NOT NULL,
  checksum CHAR(64) NULL,
  applied_at DATETIME NOT NULL,
  PRIMARY KEY (filename)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_sv_0900_ai_ci;
