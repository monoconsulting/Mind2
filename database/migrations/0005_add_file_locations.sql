-- Optional table to store capture location metadata
CREATE TABLE IF NOT EXISTS file_locations (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  file_id VARCHAR(36) NOT NULL,
  lat DOUBLE NULL,
  lon DOUBLE NULL,
  acc DOUBLE NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
DROP PROCEDURE IF EXISTS create_index_if_not_exists;
CREATE PROCEDURE create_index_if_not_exists()
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM INFORMATION_SCHEMA.STATISTICS
		WHERE TABLE_SCHEMA = DATABASE()
		AND TABLE_NAME = 'file_locations'
		AND INDEX_NAME = 'idx_file_locations_file'
	) THEN
		CREATE INDEX idx_file_locations_file ON file_locations (file_id);
	END IF;
END;

CALL create_index_if_not_exists();
DROP PROCEDURE IF EXISTS create_index_if_not_exists;

