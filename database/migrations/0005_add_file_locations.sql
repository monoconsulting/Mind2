-- Optional table to store capture location metadata
CREATE TABLE IF NOT EXISTS file_locations (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  file_id VARCHAR(36) NOT NULL,
  lat DOUBLE NULL,
  lon DOUBLE NULL,
  acc DOUBLE NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_file_locations_file ON file_locations (file_id);

