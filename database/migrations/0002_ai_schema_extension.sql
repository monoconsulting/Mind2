-- AI schema extension: ai columns and processing tables
-- MySQL 8 does not support IF NOT EXISTS for ADD COLUMN in all versions; apply separately and allow duplicate errors
ALTER TABLE unified_files
  ADD COLUMN ai_status VARCHAR(32) NULL;
ALTER TABLE unified_files
  ADD COLUMN ai_confidence FLOAT NULL;

CREATE TABLE IF NOT EXISTS ai_processing_queue (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  file_id VARCHAR(36) NOT NULL,
  job_type VARCHAR(64) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_processing_history (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  file_id VARCHAR(36) NOT NULL,
  job_type VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
