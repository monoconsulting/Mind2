-- Create file_suffix table and add missing columns to unified_files

CREATE TABLE IF NOT EXISTS file_suffix (
  id INT AUTO_INCREMENT PRIMARY KEY,
  file_ending VARCHAR(255) NOT NULL,
  file_type INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Insert default file types
INSERT INTO file_suffix (id, file_ending, file_type, created_at) VALUES
(1, 'jpg', 1, NOW()),
(2, 'jpeg', 1, NOW()),
(3, 'png', 1, NOW()),
(4, 'mp4', 4, NOW()),
(5, 'mkv', 4, NOW()),
(6, 'gif', 1, NOW()),
(7, 'webp', 1, NOW()),
(8, 'mp3', 2, NOW()),
(9, 'wav', 2, NOW()),
(10, 'doc', 5, NOW()),
(11, 'docx', 5, NOW()),
(12, 'pdf', 5, NOW()),
(13, 'txt', 5, NOW()),
(14, 'json', 5, NOW())
ON DUPLICATE KEY UPDATE file_ending=VALUES(file_ending);

-- Add missing columns to unified_files (check if they exist first by trying)
SET @exist_file_suffix := (SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'unified_files' AND COLUMN_NAME = 'file_suffix');
SET @exist_file_category := (SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'unified_files' AND COLUMN_NAME = 'file_category');

SET @sql_suffix = IF(@exist_file_suffix = 0,
  'ALTER TABLE unified_files ADD COLUMN file_suffix VARCHAR(32) NULL COMMENT "File extension without dot"',
  'SELECT "Column file_suffix already exists" AS msg');
PREPARE stmt_suffix FROM @sql_suffix;
EXECUTE stmt_suffix;
DEALLOCATE PREPARE stmt_suffix;

SET @sql_category = IF(@exist_file_category = 0,
  'ALTER TABLE unified_files ADD COLUMN file_category INT NULL COMMENT "Reference to file_categories.id"',
  'SELECT "Column file_category already exists" AS msg');
PREPARE stmt_category FROM @sql_category;
EXECUTE stmt_category;
DEALLOCATE PREPARE stmt_category;