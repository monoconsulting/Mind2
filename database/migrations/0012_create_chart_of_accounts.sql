-- Create chart of accounts table for BAS 2025
CREATE TABLE IF NOT EXISTS chart_of_accounts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  main_account VARCHAR(10) NULL,
  main_account_description VARCHAR(255) NULL,
  no_k2 TINYINT(1) NULL,
  simple_account VARCHAR(10) NULL,
  sub_account VARCHAR(10) NULL,
  sub_account_description VARCHAR(255) NULL,
  KEY idx_main_account (main_account),
  KEY idx_sub_account (sub_account)
);