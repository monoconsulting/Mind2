-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Värd: mysql:3306
-- Tid vid skapande: 03 okt 2025 kl 06:53
-- Serverversion: 8.4.6
-- PHP-version: 8.2.27

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Databas: `mono_se_db_9`
--

-- --------------------------------------------------------

--
-- Tabellstruktur `ai_accounting_proposals`
--

CREATE TABLE `ai_accounting_proposals` (
  `id` bigint NOT NULL,
  `receipt_id` varchar(36) NOT NULL,
  `item_id` int DEFAULT NULL,
  `account_code` varchar(32) NOT NULL,
  `debit` decimal(12,2) NOT NULL DEFAULT '0.00',
  `credit` decimal(12,2) NOT NULL DEFAULT '0.00',
  `vat_rate` decimal(6,2) DEFAULT NULL,
  `notes` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Tabellstruktur `ai_llm`
--

CREATE TABLE `ai_llm` (
  `id` int NOT NULL,
  `provider_name` varchar(100) NOT NULL,
  `own_name` varchar(255) DEFAULT NULL,
  `api_key` text,
  `endpoint_url` text,
  `enabled` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `ai_llm`
--

INSERT INTO `ai_llm` (`id`, `provider_name`, `own_name`, `api_key`, `endpoint_url`, `enabled`, `created_at`, `updated_at`) VALUES
(1, 'OpenAI', 'OpenAI', '', 'put_your_api_key_here', 1, '2025-09-30 13:00:46', '2025-10-02 10:46:26'),
(2, 'Ollama', 'Local Ollama', 'put_your_api_key_here', 'http://host.docker.internal:11435', 1, '2025-10-02 05:44:15', '2025-10-02 06:11:24'),
(3, 'Anthropic', 'Claude Sonnet', 'put_your_api_key_here', '', 1, '2025-10-02 06:08:36', '2025-10-02 06:08:36');

-- --------------------------------------------------------

--
-- Tabellstruktur `ai_llm_model`
--

CREATE TABLE `ai_llm_model` (
  `id` int NOT NULL,
  `llm_id` int NOT NULL,
  `model_name` varchar(255) NOT NULL,
  `display_name` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `ai_llm_model`
--

INSERT INTO `ai_llm_model` (`id`, `llm_id`, `model_name`, `display_name`, `is_active`, `created_at`) VALUES
(1, 1, 'gpt-5-mini', 'gpt-5-mini', 1, '2025-09-30 13:01:21'),
(2, 2, 'gpt-oss-20b', 'gpt-oss-20b', 1, '2025-10-02 05:44:32'),
(3, 3, 'claude-sonnet-4.5', 'claude-sonnet-4.5', 1, '2025-10-02 06:09:00');

-- --------------------------------------------------------

--
-- Tabellstruktur `ai_processing_history`
--

CREATE TABLE `ai_processing_history` (
  `id` bigint NOT NULL,
  `file_id` varchar(36) NOT NULL,
  `job_type` varchar(64) NOT NULL,
  `status` varchar(32) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `ai_stage_name` varchar(64) DEFAULT NULL COMMENT 'Human-readable AI stage name (AI1-DocumentClassification, AI2-ExpenseClassification, etc.)',
  `log_text` text COMMENT 'Detailed log message explaining what happened in this stage',
  `error_message` text COMMENT 'Error message if the stage failed',
  `confidence` float DEFAULT NULL COMMENT 'Confidence score for this AI stage result',
  `processing_time_ms` int DEFAULT NULL COMMENT 'Processing time in milliseconds',
  `provider` varchar(64) DEFAULT NULL COMMENT 'AI provider used (rule-based, openai, azure, etc.)',
  `model_name` varchar(128) DEFAULT NULL COMMENT 'Model name used for this stage'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `ai_processing_history`
--

INSERT INTO `ai_processing_history` (`id`, `file_id`, `job_type`, `status`, `created_at`, `ai_stage_name`, `log_text`, `error_message`, `confidence`, `processing_time_ms`, `provider`, `model_name`) VALUES
(1, '260eff03-ce39-4218-aed7-a0207b4883b7', 'ftp_fetch', 'success', '2025-10-02 14:25:15', 'FTP-FileFetched', 'File fetched from FTP: filename=photo_68bdc1cc97f643.62743853.jpg, size=1629839 bytes, hash=c0e6ea569eb30475..., metadata_fields=[\'file_id\', \'filename\', \'original_name\', \'timestamp\', \'location\', \'tags\', \'session_id\', \'file_size\', \'file_type\']', NULL, NULL, NULL, 'ftp', NULL),
(2, 'd6173f97-95d1-4aa7-8ae2-70bdd7e447a4', 'ftp_fetch', 'success', '2025-10-02 14:25:16', 'FTP-FileFetched', 'File fetched from FTP: filename=photo_68b6739890f7a7.62128365.jpg, size=2185897 bytes, hash=c5755c411da65591..., metadata_fields=[\'file_id\', \'filename\', \'original_name\', \'timestamp\', \'location\', \'tags\', \'session_id\', \'file_size\', \'file_type\']', NULL, NULL, NULL, 'ftp', NULL),
(3, '77033392-3f8e-4679-88ff-051405f5ff39', 'ftp_fetch', 'success', '2025-10-02 14:25:16', 'FTP-FileFetched', 'File fetched from FTP: filename=photo_68bc1fcb8fb2d1.19853966.jpg, size=2116861 bytes, hash=a9edb34d2e091191..., metadata_fields=[\'file_id\', \'filename\', \'original_name\', \'timestamp\', \'location\', \'tags\', \'session_id\', \'file_size\', \'file_type\']', NULL, NULL, NULL, 'ftp', NULL),
(4, '595466b8-ed50-4a98-a248-8760aa14abb1', 'ftp_fetch', 'success', '2025-10-02 14:25:17', 'FTP-FileFetched', 'File fetched from FTP: filename=photo_68be7ad9d1e7c3.81863965.jpg, size=2142684 bytes, hash=ab9061e7f57851ff..., metadata_fields=[\'file_id\', \'filename\', \'original_name\', \'timestamp\', \'location\', \'tags\', \'session_id\', \'file_size\', \'file_type\']', NULL, NULL, NULL, 'ftp', NULL),
(5, '6495a8b5-7a4f-410f-90c0-3ff0b46d2614', 'ftp_fetch', 'success', '2025-10-02 14:25:17', 'FTP-FileFetched', 'File fetched from FTP: filename=photo_68b4a0e12436a2.02743784.jpg, size=1169356 bytes, hash=f9c254e178e48b22..., metadata_fields=[\'file_id\', \'filename\', \'original_name\', \'timestamp\', \'location\', \'tags\', \'session_id\', \'file_size\', \'file_type\']', NULL, NULL, NULL, 'ftp', NULL),
(6, 'c1d28ed8-e733-42e2-ace6-5c3c796a9263', 'ftp_fetch', 'success', '2025-10-02 14:25:18', 'FTP-FileFetched', 'File fetched from FTP: filename=photo_68d51dec3d2445.62262545.jpg, size=2863045 bytes, hash=3ae2e5f808a0893c..., metadata_fields=[\'file_id\', \'filename\', \'original_name\', \'timestamp\', \'location\', \'tags\', \'session_id\', \'file_size\', \'file_type\']', NULL, NULL, NULL, 'ftp', NULL),
(7, 'b89b6b81-3b0b-44bd-ad44-31e3c40eb063', 'ftp_fetch', 'success', '2025-10-02 14:25:18', 'FTP-FileFetched', 'File fetched from FTP: filename=photo_68c39c92096163.69462592.jpg, size=1871790 bytes, hash=fae9bf507129426a..., metadata_fields=[\'file_id\', \'filename\', \'original_name\', \'timestamp\', \'location\', \'tags\', \'session_id\', \'file_size\', \'file_type\']', NULL, NULL, NULL, 'ftp', NULL),
(8, '8b8bae38-1e69-4c21-98b8-c3fcf968410f', 'ftp_fetch', 'success', '2025-10-02 14:25:19', 'FTP-FileFetched', 'File fetched from FTP: filename=photo_68b5d14befd6b8.95349031.jpg, size=1143142 bytes, hash=e5777f432af09597..., metadata_fields=[\'file_id\', \'filename\', \'original_name\', \'timestamp\', \'location\', \'tags\', \'session_id\', \'file_size\', \'file_type\']', NULL, NULL, NULL, 'ftp', NULL),
(9, '88809954-11ec-4708-a932-e6566adfec72', 'ftp_fetch', 'success', '2025-10-02 14:25:19', 'FTP-FileFetched', 'File fetched from FTP: filename=photo_68bb122a63d1b1.20796996.jpg, size=1891504 bytes, hash=ba61e4815c80549a..., metadata_fields=[\'file_id\', \'filename\', \'original_name\', \'timestamp\', \'location\', \'tags\', \'session_id\', \'file_size\', \'file_type\']', NULL, NULL, NULL, 'ftp', NULL),
(10, '260eff03-ce39-4218-aed7-a0207b4883b7', 'ocr', 'success', '2025-10-02 14:25:26', 'OCR-TextExtraction', 'OCR completed successfully: extracted 0 characters of raw text; detected: merchant=\'Demo Shop\', amount=123.45', NULL, NULL, 6087, 'paddleocr', NULL),
(11, '6495a8b5-7a4f-410f-90c0-3ff0b46d2614', 'ocr', 'success', '2025-10-02 14:27:23', 'OCR-TextExtraction', 'OCR completed successfully: extracted 20 characters of raw text; preview: \'aekcat VRPTEN ENO on\'; detected: merchant=\'aekcat\'', NULL, NULL, 117091, 'paddleocr', NULL),
(12, 'd6173f97-95d1-4aa7-8ae2-70bdd7e447a4', 'ocr', 'success', '2025-10-02 14:27:29', 'OCR-TextExtraction', 'OCR completed successfully: extracted 301 characters of raw text; preview: \'Ej kvitto UBEREATS #76868 Hemleverans 16:00 2025-09-01 Framme: Mattias Namn: 8 586 970 68 +46 Tel: 7...\'; detected: merchant=\'Ej\', date=2025-09-01', NULL, NULL, 129380, 'paddleocr', NULL),
(13, '595466b8-ed50-4a98-a248-8760aa14abb1', 'ocr', 'success', '2025-10-02 14:27:42', 'OCR-TextExtraction', 'OCR completed successfully: extracted 251 characters of raw text; preview: \'SE MS Handelsban 30308472 BUTIKSNR: TERM: 40956913-1073220 2025-09-08 08:40 Visa DEBIT Contactless *...\'; detected: merchant=\'SE\', amount=358.9, date=2025-09-08', NULL, NULL, 142686, 'paddleocr', NULL),
(14, '77033392-3f8e-4679-88ff-051405f5ff39', 'ocr', 'success', '2025-10-02 14:28:31', 'OCR-TextExtraction', 'OCR completed successfully: extracted 484 characters of raw text; preview: \'123 122 8 OGOORA 261.80 SER AAX 824 PERIOD : 00 RRRES RAT 5102696 392192 PERS TVR: 0000000000 wd AID...\'; detected: merchant=\'123\', amount=261.8, date=2025-09-06', NULL, NULL, 191443, 'paddleocr', NULL),
(15, 'c1d28ed8-e733-42e2-ace6-5c3c796a9263', 'ocr', 'success', '2025-10-02 14:28:35', 'OCR-TextExtraction', 'OCR completed successfully: extracted 469 characters of raw text; preview: \'VERIFIERAD AV ENHET DEBIT PSN:00 Visa VISA CONTACTLESS 3632 XXXX XXXX XXXX 04709418-106957 TERM 3057...\'; detected: merchant=\'VERIFIERAD AV ENHET\', amount=313.0, date=2025-09-07', NULL, NULL, 71965, 'paddleocr', NULL),
(16, '260eff03-ce39-4218-aed7-a0207b4883b7', 'ai1', 'success', '2025-10-02 14:28:36', 'AI1-DocumentClassification', 'Classified document as \'Manual Review\'; OCR text length: 0 characters; Reasoning: Prompt hint provided: AI 1: \"You are an AI model receiving text from a scanned document.\nDetermine the document type: \"receipt\", \"invoice\", or \"other\".\nFocus on text clues (e.g., words like \"KVITTO\", \"FAKTURA\", \"VAT\", company names, reference numbers).\nRespond with ONLY one of these three labels without explanation ', NULL, 0, 1568, 'openai', 'gpt-5-mini'),
(17, '260eff03-ce39-4218-aed7-a0207b4883b7', 'ai2', 'success', '2025-10-02 14:28:38', 'AI2-ExpenseClassification', 'Classified expense as \'personal\'; Document type: Manual Review; Reasoning: Defaulting to personal expense; Prompt hint provided:  AI2: You are an AI model analyzing receipt details (payment method, card data, contextual text).\nDetermine whether the receipt is an *employee expense* or a *company card expense*.\nLook for signs such as company card names, \"FirstCard\", \"MasterCard\", or if payment is linked to employee.\nReply with either \"personal\" or \"corporate\" only, without any extra text.', NULL, 0.65, 1195, 'openai', 'gpt-5-mini'),
(18, '8b8bae38-1e69-4c21-98b8-c3fcf968410f', 'ocr', 'success', '2025-10-02 14:28:45', 'OCR-TextExtraction', 'OCR completed successfully: extracted 304 characters of raw text; preview: \'EJ kvitto UBEREATS #76868 Henleverans Framne: 2025-09-01 16:00 Nann: Mattias 8 580 970 68 Tel: +46 T...\'; detected: merchant=\'EJ kvitto\', date=2025-09-01', NULL, NULL, 62840, 'paddleocr', NULL),
(19, '6495a8b5-7a4f-410f-90c0-3ff0b46d2614', 'ai1', 'success', '2025-10-02 14:28:47', 'AI1-DocumentClassification', 'Classified document as \'other\'; OCR text length: 20 characters; Reasoning: Generic document with limited keywords; Prompt hint provided: AI 1: \"You are an AI model receiving text from a scanned document.\nDetermine the document type: \"receipt\", \"invoice\", or \"other\".\nFocus on text clues (e.g., words like \"KVITTO\", \"FAKTURA\", \"VAT\", company names, reference numbers).\nRespond with ONLY one of these three labels without explanation ', NULL, 0.5, 1251, 'openai', 'gpt-5-mini'),
(20, '260eff03-ce39-4218-aed7-a0207b4883b7', 'ai3', 'success', '2025-10-02 14:28:47', 'AI3-DataExtraction', 'Extracted data: expense_type=personal; Company: country=\'Sweden\'; Items: 0 total', NULL, 0, 9428, 'openai', 'gpt-5-mini'),
(21, '6495a8b5-7a4f-410f-90c0-3ff0b46d2614', 'ai2', 'success', '2025-10-02 14:28:47', 'AI2-ExpenseClassification', 'Classified expense as \'personal\'; Document type: other; Reasoning: Defaulting to personal expense; Prompt hint provided:  AI2: You are an AI model analyzing receipt details (payment method, card data, contextual text).\nDetermine whether the receipt is an *employee expense* or a *company card expense*.\nLook for signs such as company card names, \"FirstCard\", \"MasterCard\", or if payment is linked to employee.\nReply with either \"personal\" or \"corporate\" only, without any extra text.', NULL, 0.65, 607, 'openai', 'gpt-5-mini'),
(22, '260eff03-ce39-4218-aed7-a0207b4883b7', 'ai4', 'success', '2025-10-02 14:28:49', 'AI4-AccountingClassification', 'Generated 0 accounting proposals; Vendor: N/A; Amounts: gross=0, net=0, vat=0; Based on BAS 2025 chart of accounts', NULL, 0, 1530, 'openai', 'gpt-5-mini'),
(23, '260eff03-ce39-4218-aed7-a0207b4883b7', 'ai5', 'skipped', '2025-10-02 14:28:49', 'AI5-CreditCardMatching', 'Skipped: No purchase_datetime available for matching', NULL, NULL, NULL, NULL, NULL),
(24, '260eff03-ce39-4218-aed7-a0207b4883b7', 'ai_pipeline', 'success', '2025-10-02 14:28:49', 'Pipeline-Complete', 'Completed 4 AI stages successfully: AI1, AI2, AI3, AI4', NULL, NULL, 14449, NULL, NULL),
(25, 'd6173f97-95d1-4aa7-8ae2-70bdd7e447a4', 'ai1', 'success', '2025-10-02 14:28:50', 'AI1-DocumentClassification', 'Classified document as \'receipt\'; OCR text length: 301 characters; Reasoning: Receipt keywords detected; Prompt hint provided: AI 1: \"You are an AI model receiving text from a scanned document.\nDetermine the document type: \"receipt\", \"invoice\", or \"other\".\nFocus on text clues (e.g., words like \"KVITTO\", \"FAKTURA\", \"VAT\", company names, reference numbers).\nRespond with ONLY one of these three labels without explanation ', NULL, 0.5, 711, 'openai', 'gpt-5-mini'),
(26, 'd6173f97-95d1-4aa7-8ae2-70bdd7e447a4', 'ai2', 'success', '2025-10-02 14:28:51', 'AI2-ExpenseClassification', 'Classified expense as \'personal\'; Document type: receipt; Reasoning: Defaulting to personal expense; Prompt hint provided:  AI2: You are an AI model analyzing receipt details (payment method, card data, contextual text).\nDetermine whether the receipt is an *employee expense* or a *company card expense*.\nLook for signs such as company card names, \"FirstCard\", \"MasterCard\", or if payment is linked to employee.\nReply with either \"personal\" or \"corporate\" only, without any extra text.', NULL, 0.65, 935, 'openai', 'gpt-5-mini'),
(27, '6495a8b5-7a4f-410f-90c0-3ff0b46d2614', 'ai3', 'success', '2025-10-02 14:29:00', 'AI3-DataExtraction', 'Extracted data: expense_type=personal; Company: name=\'aekcat\'; country=\'Sweden\'; Items: 0 total', NULL, 0.25, 12978, 'openai', 'gpt-5-mini'),
(28, 'b89b6b81-3b0b-44bd-ad44-31e3c40eb063', 'ocr', 'success', '2025-10-02 14:29:01', 'OCR-TextExtraction', 'OCR completed successfully: extracted 963 characters of raw text; preview: \'HORNBACH Det finns alltid gōra. nät tatt Hornbach By99marknad AB Filial 773 Madenvägen 17 174 55 Sun...\'; detected: merchant=\'HORNBACH\', amount=313.0, date=2025-09-07', NULL, NULL, 91604, 'paddleocr', NULL),
(29, '6495a8b5-7a4f-410f-90c0-3ff0b46d2614', 'ai4', 'success', '2025-10-02 14:29:01', 'AI4-AccountingClassification', 'Generated 0 accounting proposals; Vendor: N/A; Amounts: gross=0, net=0, vat=0; Based on BAS 2025 chart of accounts', NULL, 0, 464, 'openai', 'gpt-5-mini'),
(30, '6495a8b5-7a4f-410f-90c0-3ff0b46d2614', 'ai5', 'skipped', '2025-10-02 14:29:01', 'AI5-CreditCardMatching', 'Skipped: No purchase_datetime available for matching', NULL, NULL, NULL, NULL, NULL),
(31, '6495a8b5-7a4f-410f-90c0-3ff0b46d2614', 'ai_pipeline', 'success', '2025-10-02 14:29:01', 'Pipeline-Complete', 'Completed 4 AI stages successfully: AI1, AI2, AI3, AI4', NULL, NULL, 15754, NULL, NULL),
(32, '595466b8-ed50-4a98-a248-8760aa14abb1', 'ai1', 'success', '2025-10-02 14:29:01', 'AI1-DocumentClassification', 'Classified document as \'receipt\'; OCR text length: 251 characters; Reasoning: Receipt keywords detected; Prompt hint provided: AI 1: \"You are an AI model receiving text from a scanned document.\nDetermine the document type: \"receipt\", \"invoice\", or \"other\".\nFocus on text clues (e.g., words like \"KVITTO\", \"FAKTURA\", \"VAT\", company names, reference numbers).\nRespond with ONLY one of these three labels without explanation ', NULL, 0.5, 395, 'openai', 'gpt-5-mini'),
(33, '77033392-3f8e-4679-88ff-051405f5ff39', 'ai1', 'success', '2025-10-02 14:29:01', 'AI1-DocumentClassification', 'Classified document as \'receipt\'; OCR text length: 484 characters; Reasoning: Receipt keywords detected; Prompt hint provided: AI 1: \"You are an AI model receiving text from a scanned document.\nDetermine the document type: \"receipt\", \"invoice\", or \"other\".\nFocus on text clues (e.g., words like \"KVITTO\", \"FAKTURA\", \"VAT\", company names, reference numbers).\nRespond with ONLY one of these three labels without explanation ', NULL, 0.6, 360, 'openai', 'gpt-5-mini'),
(34, '595466b8-ed50-4a98-a248-8760aa14abb1', 'ai2', 'success', '2025-10-02 14:29:02', 'AI2-ExpenseClassification', 'Classified expense as \'corporate\'; Document type: receipt; Card identifier: visa; Reasoning: Detected card keyword \'visa\'; Prompt hint provided:  AI2: You are an AI model analyzing receipt details (payment method, card data, contextual text).\nDetermine whether the receipt is an *employee expense* or a *company card expense*.\nLook for signs such as company card names, \"FirstCard\", \"MasterCard\", or if payment is linked to employee.\nReply with either \"personal\" or \"corporate\" only, without any extra text.', NULL, 0.85, 390, 'openai', 'gpt-5-mini'),
(35, '77033392-3f8e-4679-88ff-051405f5ff39', 'ai2', 'success', '2025-10-02 14:29:02', 'AI2-ExpenseClassification', 'Classified expense as \'personal\'; Document type: receipt; Reasoning: Defaulting to personal expense; Prompt hint provided:  AI2: You are an AI model analyzing receipt details (payment method, card data, contextual text).\nDetermine whether the receipt is an *employee expense* or a *company card expense*.\nLook for signs such as company card names, \"FirstCard\", \"MasterCard\", or if payment is linked to employee.\nReply with either \"personal\" or \"corporate\" only, without any extra text.', NULL, 0.65, 321, 'openai', 'gpt-5-mini'),
(36, '88809954-11ec-4708-a932-e6566adfec72', 'ocr', 'success', '2025-10-02 14:29:04', 'OCR-TextExtraction', 'OCR completed successfully: extracted 262 characters of raw text; preview: \'SKA UTGANG MS Handelsban SE BUTIKSNR: _30308472 TERM: 40956875-1073220 2025-09-05 18:32 Visa DEBIT C...\'; detected: merchant=\'SKA\', amount=84.95, date=2025-09-05', NULL, NULL, 33308, 'paddleocr', NULL),
(37, 'c1d28ed8-e733-42e2-ace6-5c3c796a9263', 'ai1', 'success', '2025-10-02 14:29:06', 'AI1-DocumentClassification', 'Classified document as \'receipt\'; OCR text length: 469 characters; Reasoning: Receipt keywords detected; Prompt hint provided: AI 1: \"You are an AI model receiving text from a scanned document.\nDetermine the document type: \"receipt\", \"invoice\", or \"other\".\nFocus on text clues (e.g., words like \"KVITTO\", \"FAKTURA\", \"VAT\", company names, reference numbers).\nRespond with ONLY one of these three labels without explanation ', NULL, 0.6, 1062, 'openai', 'gpt-5-mini'),
(38, 'c1d28ed8-e733-42e2-ace6-5c3c796a9263', 'ai2', 'success', '2025-10-02 14:29:06', 'AI2-ExpenseClassification', 'Classified expense as \'corporate\'; Document type: receipt; Card identifier: visa; Reasoning: Detected card keyword \'visa\'; Prompt hint provided:  AI2: You are an AI model analyzing receipt details (payment method, card data, contextual text).\nDetermine whether the receipt is an *employee expense* or a *company card expense*.\nLook for signs such as company card names, \"FirstCard\", \"MasterCard\", or if payment is linked to employee.\nReply with either \"personal\" or \"corporate\" only, without any extra text.', NULL, 0.85, 566, 'openai', 'gpt-5-mini'),
(39, 'd6173f97-95d1-4aa7-8ae2-70bdd7e447a4', 'ai3', 'success', '2025-10-02 14:29:16', 'AI3-DataExtraction', 'Extracted data: gross=660.0, gross_sek=660, currency=SEK, purchase_date=2025-09-01 16:00:00, expense_type=personal; Company: name=\'UBEREATS\'; country=\'Sweden\'; Items: 3 total; Sample items: [Con Carne Rigatoni Original 33cl Coca-Cola@220.0, Con Carne Rigatoni Coca-Cola Zero 33cl@220.0, Con Carne Rigatoni Coca-Cola Zero 33cl@220.0]', NULL, 0.65, 25013, 'openai', 'gpt-5-mini'),
(40, 'd6173f97-95d1-4aa7-8ae2-70bdd7e447a4', 'ai4', 'success', '2025-10-02 14:29:17', 'AI4-AccountingClassification', 'Generated 0 accounting proposals; Vendor: N/A; Amounts: gross=660, net=0, vat=660; Based on BAS 2025 chart of accounts', NULL, 0, 292, 'openai', 'gpt-5-mini'),
(41, 'd6173f97-95d1-4aa7-8ae2-70bdd7e447a4', 'ai5', 'success', '2025-10-02 14:29:17', 'AI5-CreditCardMatching', 'Match result: NOT MATCHED; Search criteria: merchant=\'None\', amount=660, date=2025-09-01 16:00:00; Reason: No transaction met the criteria', NULL, 0.45, 35, 'openai', 'gpt-5-mini'),
(42, 'd6173f97-95d1-4aa7-8ae2-70bdd7e447a4', 'ai_pipeline', 'success', '2025-10-02 14:29:17', 'Pipeline-Complete', 'Completed 5 AI stages successfully: AI1, AI2, AI3, AI4, AI5', NULL, NULL, 27313, NULL, NULL),
(43, '8b8bae38-1e69-4c21-98b8-c3fcf968410f', 'ai1', 'success', '2025-10-02 14:29:17', 'AI1-DocumentClassification', 'Classified document as \'receipt\'; OCR text length: 304 characters; Reasoning: Receipt keywords detected; Prompt hint provided: AI 1: \"You are an AI model receiving text from a scanned document.\nDetermine the document type: \"receipt\", \"invoice\", or \"other\".\nFocus on text clues (e.g., words like \"KVITTO\", \"FAKTURA\", \"VAT\", company names, reference numbers).\nRespond with ONLY one of these three labels without explanation ', NULL, 0.5, 299, 'openai', 'gpt-5-mini'),
(44, '8b8bae38-1e69-4c21-98b8-c3fcf968410f', 'ai2', 'success', '2025-10-02 14:29:18', 'AI2-ExpenseClassification', 'Classified expense as \'personal\'; Document type: receipt; Reasoning: Defaulting to personal expense; Prompt hint provided:  AI2: You are an AI model analyzing receipt details (payment method, card data, contextual text).\nDetermine whether the receipt is an *employee expense* or a *company card expense*.\nLook for signs such as company card names, \"FirstCard\", \"MasterCard\", or if payment is linked to employee.\nReply with either \"personal\" or \"corporate\" only, without any extra text.', NULL, 0.65, 808, 'openai', 'gpt-5-mini'),
(45, '595466b8-ed50-4a98-a248-8760aa14abb1', 'ai3', 'success', '2025-10-02 14:29:28', 'AI3-DataExtraction', 'Extracted data: gross=358.9, gross_sek=359, currency=SEK, purchase_date=2025-09-08 08:40:00, payment_type=card, expense_type=corporate, receipt_number=517982 135108 KF1; Company: name=\'BAUHAUS\'; city=\'Bromma\'; zip=\'16867\'; country=\'Sweden\'; Items: 1 total; Sample items: [Köp@358.9]', NULL, 0.78, 26781, 'openai', 'gpt-5-mini'),
(46, '595466b8-ed50-4a98-a248-8760aa14abb1', 'ai4', 'success', '2025-10-02 14:29:29', 'AI4-AccountingClassification', 'Generated 0 accounting proposals; Vendor: BAUHAUS; Amounts: gross=359, net=0, vat=359; Based on BAS 2025 chart of accounts', NULL, 0, 365, 'openai', 'gpt-5-mini'),
(47, '595466b8-ed50-4a98-a248-8760aa14abb1', 'ai5', 'success', '2025-10-02 14:29:29', 'AI5-CreditCardMatching', 'Match result: NOT MATCHED; Search criteria: merchant=\'BAUHAUS\', amount=359, date=2025-09-08 08:40:00; Reason: No transaction met the criteria', NULL, 0.45, 33, 'openai', 'gpt-5-mini'),
(48, '595466b8-ed50-4a98-a248-8760aa14abb1', 'ai_pipeline', 'success', '2025-10-02 14:29:29', 'Pipeline-Complete', 'Completed 5 AI stages successfully: AI1, AI2, AI3, AI4, AI5', NULL, NULL, 28117, NULL, NULL),
(49, 'b89b6b81-3b0b-44bd-ad44-31e3c40eb063', 'ai1', 'success', '2025-10-02 14:29:29', 'AI1-DocumentClassification', 'Classified document as \'receipt\'; OCR text length: 963 characters; Reasoning: Receipt keywords detected; Prompt hint provided: AI 1: \"You are an AI model receiving text from a scanned document.\nDetermine the document type: \"receipt\", \"invoice\", or \"other\".\nFocus on text clues (e.g., words like \"KVITTO\", \"FAKTURA\", \"VAT\", company names, reference numbers).\nRespond with ONLY one of these three labels without explanation ', NULL, 0.8, 302, 'openai', 'gpt-5-mini'),
(50, 'b89b6b81-3b0b-44bd-ad44-31e3c40eb063', 'ai2', 'success', '2025-10-02 14:29:30', 'AI2-ExpenseClassification', 'Classified expense as \'corporate\'; Document type: receipt; Card identifier: visa; Reasoning: Detected card keyword \'visa\'; Prompt hint provided:  AI2: You are an AI model analyzing receipt details (payment method, card data, contextual text).\nDetermine whether the receipt is an *employee expense* or a *company card expense*.\nLook for signs such as company card names, \"FirstCard\", \"MasterCard\", or if payment is linked to employee.\nReply with either \"personal\" or \"corporate\" only, without any extra text.', NULL, 0.85, 277, 'openai', 'gpt-5-mini'),
(51, 'c1d28ed8-e733-42e2-ace6-5c3c796a9263', 'ai3', 'success', '2025-10-02 14:29:38', 'AI3-DataExtraction', 'Extracted data: gross=313.0, net=250.4, currency=AED, purchase_date=2025-09-07 12:13:00, payment_type=card, expense_type=corporate, receipt_number=106957; Company: country=\'Sweden\'; Items: 0 total', NULL, 0.55, 31550, 'openai', 'gpt-5-mini'),
(52, '77033392-3f8e-4679-88ff-051405f5ff39', 'ai3', 'success', '2025-10-02 14:29:38', 'AI3-DataExtraction', 'Extracted data: gross=261.8, net=209.44, gross_sek=262, net_sek=209, currency=SEK, purchase_date=2025-09-06 13:46:00, payment_type=card, expense_type=personal, receipt_number=5102696; Company: name=\'OGOORA\'; address=\'KarIsbodavägen\'; country=\'Sweden\'; Items: 1 total; Sample items: [Unknown item@261.8]', NULL, 0.45, 35946, 'openai', 'gpt-5-mini'),
(53, 'c1d28ed8-e733-42e2-ace6-5c3c796a9263', 'ai4', 'success', '2025-10-02 14:29:38', 'AI4-AccountingClassification', 'Generated 0 accounting proposals; Vendor: N/A; Amounts: gross=0, net=0, vat=0; Based on BAS 2025 chart of accounts', NULL, 0, 363, 'openai', 'gpt-5-mini'),
(54, '77033392-3f8e-4679-88ff-051405f5ff39', 'ai4', 'success', '2025-10-02 14:29:38', 'AI4-AccountingClassification', 'Generated 0 accounting proposals; Vendor: N/A; Amounts: gross=262, net=209, vat=53; Based on BAS 2025 chart of accounts', NULL, 0, 316, 'openai', 'gpt-5-mini'),
(55, 'c1d28ed8-e733-42e2-ace6-5c3c796a9263', 'ai5', 'success', '2025-10-02 14:29:38', 'AI5-CreditCardMatching', 'Match result: NOT MATCHED; Search criteria: merchant=\'None\', amount=0, date=2025-09-07 12:13:00; Reason: No transaction met the criteria', NULL, 0.45, 40, 'openai', 'gpt-5-mini'),
(56, 'c1d28ed8-e733-42e2-ace6-5c3c796a9263', 'ai_pipeline', 'success', '2025-10-02 14:29:38', 'Pipeline-Complete', 'Completed 5 AI stages successfully: AI1, AI2, AI3, AI4, AI5', NULL, NULL, 33716, NULL, NULL),
(57, '77033392-3f8e-4679-88ff-051405f5ff39', 'ai5', 'success', '2025-10-02 14:29:38', 'AI5-CreditCardMatching', 'Match result: NOT MATCHED; Search criteria: merchant=\'None\', amount=262, date=2025-09-06 13:46:00; Reason: No transaction met the criteria', NULL, 0.45, 37, 'openai', 'gpt-5-mini'),
(58, '77033392-3f8e-4679-88ff-051405f5ff39', 'ai_pipeline', 'success', '2025-10-02 14:29:38', 'Pipeline-Complete', 'Completed 5 AI stages successfully: AI1, AI2, AI3, AI4, AI5', NULL, NULL, 37138, NULL, NULL),
(59, '88809954-11ec-4708-a932-e6566adfec72', 'ai1', 'success', '2025-10-02 14:29:39', 'AI1-DocumentClassification', 'Classified document as \'receipt\'; OCR text length: 262 characters; Reasoning: Receipt keywords detected; Prompt hint provided: AI 1: \"You are an AI model receiving text from a scanned document.\nDetermine the document type: \"receipt\", \"invoice\", or \"other\".\nFocus on text clues (e.g., words like \"KVITTO\", \"FAKTURA\", \"VAT\", company names, reference numbers).\nRespond with ONLY one of these three labels without explanation ', NULL, 0.5, 440, 'openai', 'gpt-5-mini'),
(60, '88809954-11ec-4708-a932-e6566adfec72', 'ai2', 'success', '2025-10-02 14:29:40', 'AI2-ExpenseClassification', 'Classified expense as \'corporate\'; Document type: receipt; Card identifier: visa; Reasoning: Detected card keyword \'visa\'; Prompt hint provided:  AI2: You are an AI model analyzing receipt details (payment method, card data, contextual text).\nDetermine whether the receipt is an *employee expense* or a *company card expense*.\nLook for signs such as company card names, \"FirstCard\", \"MasterCard\", or if payment is linked to employee.\nReply with either \"personal\" or \"corporate\" only, without any extra text.', NULL, 0.85, 971, 'openai', 'gpt-5-mini'),
(61, '8b8bae38-1e69-4c21-98b8-c3fcf968410f', 'ai3', 'success', '2025-10-02 14:29:46', 'AI3-DataExtraction', 'Extracted data: gross=660.0, gross_sek=660, currency=SEK, purchase_date=2025-09-01 16:00:00, expense_type=personal, receipt_number=#76868; Company: name=\'UBEREATS\'; country=\'Sweden\'; Items: 3 total; Sample items: [Rigatoni Con Carne + Coca Cola Original 33cl@220.0, Rigatoni Con Carne + Coca Cola Zero 33cl@220.0, Rigatoni Con Carne + Coca Cola Zero 33cl@220.0]', NULL, 0.6, 27953, 'openai', 'gpt-5-mini'),
(62, '8b8bae38-1e69-4c21-98b8-c3fcf968410f', 'ai4', 'success', '2025-10-02 14:29:46', 'AI4-AccountingClassification', 'Generated 0 accounting proposals; Vendor: N/A; Amounts: gross=660, net=0, vat=660; Based on BAS 2025 chart of accounts', NULL, 0, 344, 'openai', 'gpt-5-mini'),
(63, '8b8bae38-1e69-4c21-98b8-c3fcf968410f', 'ai5', 'success', '2025-10-02 14:29:46', 'AI5-CreditCardMatching', 'Match result: NOT MATCHED; Search criteria: merchant=\'None\', amount=660, date=2025-09-01 16:00:00; Reason: No transaction met the criteria', NULL, 0.45, 36, 'openai', 'gpt-5-mini'),
(64, '8b8bae38-1e69-4c21-98b8-c3fcf968410f', 'ai_pipeline', 'success', '2025-10-02 14:29:46', 'Pipeline-Complete', 'Completed 5 AI stages successfully: AI1, AI2, AI3, AI4, AI5', NULL, NULL, 29568, NULL, NULL),
(65, '88809954-11ec-4708-a932-e6566adfec72', 'ai3', 'success', '2025-10-02 14:30:04', 'AI3-DataExtraction', 'Extracted data: gross=84.95, gross_sek=85, currency=SEK, purchase_date=2025-09-05 18:32:00, payment_type=card, expense_type=corporate, receipt_number=577633 180359 KF1; Company: name=\'BAUHAUS\'; city=\'Bromma\'; zip=\'16867\'; country=\'Sweden\'; Items: 1 total; Sample items: [KÖP@84.95]', NULL, 0.65, 24250, 'openai', 'gpt-5-mini'),
(66, '88809954-11ec-4708-a932-e6566adfec72', 'ai4', 'success', '2025-10-02 14:30:04', 'AI4-AccountingClassification', 'Generated 0 accounting proposals; Vendor: BAUHAUS; Amounts: gross=85, net=0, vat=85; Based on BAS 2025 chart of accounts', NULL, 0, 289, 'openai', 'gpt-5-mini'),
(67, '88809954-11ec-4708-a932-e6566adfec72', 'ai5', 'success', '2025-10-02 14:30:04', 'AI5-CreditCardMatching', 'Match result: NOT MATCHED; Search criteria: merchant=\'BAUHAUS\', amount=85, date=2025-09-05 18:32:00; Reason: No transaction met the criteria', NULL, 0.45, 54, 'openai', 'gpt-5-mini'),
(68, '88809954-11ec-4708-a932-e6566adfec72', 'ai_pipeline', 'success', '2025-10-02 14:30:04', 'Pipeline-Complete', 'Completed 5 AI stages successfully: AI1, AI2, AI3, AI4, AI5', NULL, NULL, 26128, NULL, NULL),
(69, 'b89b6b81-3b0b-44bd-ad44-31e3c40eb063', 'ai3', 'success', '2025-10-02 14:30:05', 'AI3-DataExtraction', 'Extracted data: gross=313.0, net=250.4, gross_sek=313, net_sek=250, currency=SEK, purchase_date=2025-09-07 12:13:00, payment_type=card, expense_type=corporate, receipt_number=30574008; Company: name=\'HORNBACH\'; orgnr=\'556613-4853\'; address=\'Madenvägen 17\'; city=\'Sundbyberg\'; zip=\'174 55\'; country=\'Sweden\'; Items: 2 total; Sample items: [TUNNA 75L@239.0, LOCK TILL TUNNA 75L@74.0]', NULL, 0.85, 35113, 'openai', 'gpt-5-mini'),
(70, 'b89b6b81-3b0b-44bd-ad44-31e3c40eb063', 'ai4', 'success', '2025-10-02 14:30:05', 'AI4-AccountingClassification', 'Generated 0 accounting proposals; Vendor: HORNBACH; Amounts: gross=313, net=250, vat=63; Based on BAS 2025 chart of accounts', NULL, 0, 328, 'openai', 'gpt-5-mini'),
(71, 'b89b6b81-3b0b-44bd-ad44-31e3c40eb063', 'ai5', 'success', '2025-10-02 14:30:05', 'AI5-CreditCardMatching', 'Match result: NOT MATCHED; Search criteria: merchant=\'HORNBACH\', amount=313, date=2025-09-07 12:13:00; Reason: No transaction met the criteria', NULL, 0.45, 36, 'openai', 'gpt-5-mini'),
(72, 'b89b6b81-3b0b-44bd-ad44-31e3c40eb063', 'ai_pipeline', 'success', '2025-10-02 14:30:05', 'Pipeline-Complete', 'Completed 5 AI stages successfully: AI1, AI2, AI3, AI4, AI5', NULL, NULL, 36177, NULL, NULL);

-- --------------------------------------------------------

--
-- Tabellstruktur `ai_processing_queue`
--

CREATE TABLE `ai_processing_queue` (
  `id` bigint NOT NULL,
  `file_id` varchar(36) NOT NULL,
  `job_type` varchar(64) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Tabellstruktur `ai_system_prompts`
--

CREATE TABLE `ai_system_prompts` (
  `id` int NOT NULL,
  `prompt_key` varchar(100) NOT NULL,
  `title` varchar(255) NOT NULL,
  `description` text,
  `prompt_content` text,
  `selected_model_id` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `ai_system_prompts`
--

INSERT INTO `ai_system_prompts` (`id`, `prompt_key`, `title`, `description`, `prompt_content`, `selected_model_id`, `created_at`, `updated_at`) VALUES
(3, 'receipt_items_classification', 'Klassificering av kvittoposter', 'Kategoriserar och sorterar kvittodata', '**System prompt:*\n- AI3 — System Prompt (Receipt/Invoice Data Extraction → unified_files + receipt_items)\n\n  You are a deterministic data extractor for Swedish receipts and invoices.\n  Your only goal is to parse OCR text (and attached hints) into database-ready values for:\n\n  companies (one new row for each receipt/document - if the company doesn\'t exist. unified_files referes to the id in this table)\n\n  unified_files (one row per receipt/document; update only the fields you’re asked to set)\n\n  receipt_items (one row per purchased item/line)\n\n**Table: Companies**\n\nid (autogenerated)\n\nname (company name)\n\norgnr (the organization number)\n\naddress (street address or post box)\n\naddress2 (extra address)\n\nzip (zip code)\n\ncity (city)\n\ncountry (country)\n\nphone (phone number to the company)\n\nwww (homepage)\n\ncreated_at (timestamp from creation of db post)\n\nupdated_at (timestamp from updating the post)\n\n\n\n**Table: unified_files**\n\n**purchase_datetime**  - (datetime or null): derive from text; ISO YYYY-MM-DD HH:MM:SS. If only date is present, use 00:00:00. If unknown → null.\n\n**payment_type** - (varchar 255): \"card\" or \"cash\". If unknown, set \"\".\n\n**currency** - (varchar): ISO code (SEK/USD/EUR …). If nothing indicates foreign currency, use \"SEK\".\n\n**gross_amount_original** - (DECIMAL(12,2)): use values in document currency.\n\nnet_amount_original (DECIMAL(12,2)): use values in document currency.\n\n**exchange_rate** (DECIMAL(12,0), required by schema): If currency=\'SEK\' → set 0.\n\nIf foreign currency present with a decimal rate (e.g., 11.33), multiply by 100 and round to integer (1133) to comply with DECIMAL(12,0). Also include human-readable rate in other_data (e.g., \"exchange_rate_note\":\"1 USD=11.33 SEK (stored as 1133 bps)\").\n\n**gross_amount_sek** -  (INT-like DECIMAL(10,0)):  (INT-like DECIMAL(10,0)): convert to SEK and round to whole kronor (schema has no decimals). If currency is SEK, set equal to original rounded to 0 decimals.\n\n**net_amount_sek**  - (INT-like DECIMAL(10,0)):  (INT-like DECIMAL(10,0)): convert to SEK and round to whole kronor (schema has no decimals). If currency is SEK, set equal to original rounded to 0 decimals.\n\n**company_id** this id should be fetched from the companies-table for the company that wrote the receipt. If the company doesn\'t exist add it.\n\n**receipt_number:** set if unique receipt number exists on the document; else \"\".\n\n**other_data:** short JSON string or compact key=value;key=value with leftovers (e.g., terminal id, AID, reference ids).\n\n\n\n**Table: **receipt_items\n\n**main_id**: referes to the id of the main-receipt in unified_files\n\n**article_id**: (varchar 222): product/article number if present; else \"\".\n\n**name**: (varchar 222): item description/name.\n\n**number**:  (int): quantity; default 1 if not specified.\n\n**item_price_ex_vat:**, item_price_inc_vat (DECIMAL(10,2)): single-unit price (ex/incl VAT).\n\n**item_total_price_ex_vat:**, item_total_price_inc_vat (DECIMAL(10,2)): number * unit price.\n\n**currency:** (varchar 11): same as head currency.\n\n**vat:** (DECIMAL(10,2)): VAT amount per line (in document currency).\n\n**vat_percentage:** (DECIMAL(7,6)): e.g., 0.250000 for 25%, 0.120000 for 12%, 0.060000 for 6%, 0.000000 for 0%.\n\n\n\n### Normalization rules\n\n**Dates/Times:** Normalize Swedish formats (2025-09-07, 2025-09-07 12:13) to ISO. If only month/year → set day/time unknown → null for time, or use \"00:00:00\".\n\n**Numbers:** Accept both , and . as decimal separators in OCR. Convert to ..\n\n**VAT math:** Prefer explicit VAT/NET/GROSS from receipt. If only percentage is given, compute:\n\n**net** = gross / (1 + rate)\n\nvat = gross - net\nRound to 2 decimals.\n\n**Currency conversion to SEK:**\n\n- If currency=\'SEK\': gross_amount_sek ≈ round(gross_original), net_amount_sek ≈ round(net_original), exchange_rate=0.\n\n- If foreign: use given or inferred rate; store basis points in exchange_rate and keep precise rate in other_data.\n\n- \n\n## Forbidden:\n\n- Do not invent company_id. If not resolvable, keep 0.\n\n- Do not create invoice_lines matches; that is handled elsewhere.\n\n- Do not change schema-implied rounding (SEK fields are integers).\n\n```\nExample 1 — Simple SEK receipt with 25% VAT\n{\n  \"unified_files_update\": {\n    \"id\": \"9618aba4-6e2a-4c6a-8b6c-241aa825ca97\",\n    \"file_type\": \"receipt\",\n    \"purchase_datetime\": \"2025-09-07 12:13:00\",\n    \"expense_type\": \"corporate\",\n    \"payment_type\": \"card\",\n    \"orgnr\": \"5566134853\",\n    \"currency\": \"SEK\",\n    \"gross_amount_original\": 313.00,\n    \"net_amount_original\": 250.40,\n    \"exchange_rate\": 0,\n    \"gross_amount_sek\": 313,\n    \"net_amount_sek\": 250,\n    \"ai_status\": \"ok\",\n    \"ai_confidence\": 0.96,\n    \"company_id\": 2,\n    \"receipt_number\": \"55507732509070046816\",\n    \"other_data\": \"terminal=30574008;aid=A0000000031010\"\n  },\n  \"receipt_items_insert\": [\n    {\n      \"main_id\": 9618aba4-6e2a-4c6a-8b6c-241aa825ca97,\n      \"article_id\": \"\",\n      \"name\": \"Mixed goods\",\n      \"number\": 1,4\n      \"item_price_ex_vat\": 250.40,\n      \"item_price_inc_vat\": 313.00,\n      \"item_total_price_ex_vat\": 250.40,\n      \"item_total_price_inc_vat\": 313.00,\n      \"currency\": \"SEK\",\n      \"vat\": 62.60,\n      \"vat_percentage\": 0.250000\n    }\n  ]\n}\n\nExample 2 — Foreign currency (USD) with exchange rate\n{\n  \"unified_files_update\": {\n    \"id\": \"AMZ-2025-08-20-ABC\",\n    \"file_type\": \"receipt\",\n    \"purchase_datetime\": \"2025-08-20 00:00:00\",\n    \"expense_type\": \"corporate\",\n    \"payment_type\": \"card\",\n    \"orgnr\": null,\n    \"currency\": \"USD\",\n    \"gross_amount_original\": 22.00,\n    \"net_amount_original\": 20.75,\n    \"exchange_rate\": 1105,\n    \"gross_amount_sek\": 243,\n    \"net_amount_sek\": 229,\n    \"ai_status\": \"ok\",\n    \"ai_confidence\": 0.90,\n    \"company_id\": 2,\n    \"receipt_number\": \"TX-0099\",\n    \"other_data\": \"{\\\"exchange_rate_note\\\":\\\"1 USD=11.05 SEK stored as 1105 bps\\\"}\"\n  },\n  \"receipt_items_insert\": [\n    {\n      \"id\": 1\n      \"main_id\": 0,\n      \"article_id\": \"\",\n      \"name\": \"Books and stationery\",\n      \"number\": 1,\n      \"item_price_ex_vat\": 20.75,\n      \"item_price_inc_vat\": 22.00,\n      \"item_total_price_ex_vat\": 20.75,\n      \"item_total_price_inc_vat\": 22.00,\n      \"currency\": \"USD\",\n      \"vat\": 1.25,\n      \"vat_percentage\": 0.060000\n    }\n  ]\n}\n\n\n```\n\n\n\n**Validation before returning:**\n\nunified_files_update.id equals input file_id.\n\nAmount relationships per line and head hold (gross = net + VAT, within ±0.01).\n\nSEK integer fields are properly rounded; exchange_rate bps rule respected', 1, '2025-09-30 12:08:56', '2025-10-02 15:04:01'),
(4, 'accounting_classification', 'AI4: Accounting Proposals', 'Hanterar all konterings-relaterad information', '### AI4 – Accounting (Bookkeeping) Entries\n\n**Information:** \n\n**Title:** Accounting Proposals (BAS 2025)\n\n**Description:** The AI suggests accounting entries according to the Swedish BAS 2025 chart of accounts for each item. Input includes amounts and VAT details. Output should include debit/credit lines.\n\n**System prompt:**\n\n```\nYou are an AI model that receives structured receipt data including items, amounts, and VAT details. \nYour task is to generate accounting entries in accordance with Swedish accounting standards (BAS 2025). \n\nRules:\n- Always return valid JSON.\n- Each entry must map directly to the database table `ai_accounting_proposals`:\n  {\n    \"receipt_id\": \"...\",\n    \"item_id\": \"...\",\n    \"account_code\": \"BAS account number\",\n    \"debit\": \"amount in SEK (decimal)\",\n    \"credit\": \"amount in SEK (decimal)\",\n    \"vat_rate\": \"VAT rate (%)\",\n    \"notes\": \"short explanation of the entry\"\n  }\n- Use debit/credit according to double-entry bookkeeping.\n- Use BAS 2025 account codes for expenses, VAT, and payment accounts.\n- Split entries as required (e.g., expense + VAT + payment).\n- Include VAT distribution (25%, 12%, 6%) where relevant.\n- If multiple items exist, create accounting proposals per item.\n- Notes should explain the logic briefly, e.g. \"Food expense\", \"Input VAT 12%\", \"Paid with company card\".\n\n### Examples:\n\n1. **Restaurant receipt 500 SEK including 12% VAT, paid with company card (FirstCard):**\n[\n  {\n    \"receipt_id\": \"123\",\n    \"item_id\": \"A1\",\n    \"account_code\": \"6071\",\n    \"debit\": 446.43,\n    \"credit\": 0.00,\n    \"vat_rate\": 12.0,\n    \"notes\": \"Meal expense (excl VAT)\"\n  },\n  {\n    \"receipt_id\": \"123\",\n    \"item_id\": \"A1\",\n    \"account_code\": \"2641\",\n    \"debit\": 53.57,\n    \"credit\": 0.00,\n    \"vat_rate\": 12.0,\n    \"notes\": \"Input VAT 12%\"\n  },\n  {\n    \"receipt_id\": \"123\",\n    \"item_id\": \"A1\",\n    \"account_code\": \"2440\",\n    \"debit\": 0.00,\n    \"credit\": 500.00,\n    \"vat_rate\": 0.0,\n    \"notes\": \"Accounts payable / company card\"\n  }\n]\n\n2. **Office supplies 1000 SEK including 25% VAT, paid with private funds (employee reimbursement):**\n[\n  {\n    \"receipt_id\": \"456\",\n    \"item_id\": \"B2\",\n    \"account_code\": \"6110\",\n    \"debit\": 800.00,\n    \"credit\": 0.00,\n    \"vat_rate\": 25.0,\n    \"notes\": \"Office supplies expense\"\n  },\n  {\n    \"receipt_id\": \"456\",\n    \"item_id\": \"B2\",\n    \"account_code\": \"2641\",\n    \"debit\": 200.00,\n    \"credit\": 0.00,\n    \"vat_rate\": 25.0,\n    \"notes\": \"Input VAT 25%\"\n  },\n  {\n    \"receipt_id\": \"456\",\n    \"item_id\": \"B2\",\n    \"account_code\": \"2890\",\n    \"debit\": 0.00,\n    \"credit\": 1000.00,\n    \"vat_rate\": 0.0,\n    \"notes\": \"Liability to employee\"\n  }\n]\n\n3. **Taxi receipt 300 SEK including 6% VAT, paid in cash:**\n[\n  {\n    \"receipt_id\": \"789\",\n    \"item_id\": \"C3\",\n    \"account_code\": \"5611\",\n    \"debit\": 283.02,\n    \"credit\": 0.00,\n    \"vat_rate\": 6.0,\n    \"notes\": \"Travel expense (excl VAT)\"\n  },\n  {\n    \"receipt_id\": \"789\",\n    \"item_id\": \"C3\",\n    \"account_code\": \"2641\",\n    \"debit\": 16.98,\n    \"credit\": 0.00,\n    \"vat_rate\": 6.0,\n    \"notes\": \"Input VAT 6%\"\n  },\n  {\n    \"receipt_id\": \"789\",\n    \"item_id\": \"C3\",\n    \"account_code\": \"1910\",\n    \"debit\": 0.00,\n    \"credit\": 300.00,\n    \"vat_rate\": 0.0,\n    \"notes\": \"Cash payment\"\n  }\n]\n\n---\nInstructions:\n- Classify and assign accounts for all entries according to **Swedish accounting practice**.\n- Use **BAS 2025** as the reference chart of accounts.\n- Each selected account should generate an entry in `ai_accounting_proposals`.\n\n\n```\n\n\n\n- Classify and assign accounts for all entries according to **Swedish accounting practices**.\n- Use the **BAS-2025 chart of accounts**, stored in the database table `chart_of_accounts`, as the reference.\n- An entry should be made in ai_accounting_proposals for each accountnumber that is selected according to praxis', 1, '2025-09-30 12:08:56', '2025-10-03 06:18:03'),
(5, 'credit_card_matching', 'AI5: Credit Card Matching', 'Matchar FirstCard-fakturor mot befintliga kvitton', '### AI5 – Credit Card Invoice Matching\n\n- After a credit card invoice is uploaded you should compare the invoice to the receipts availbale for the pereiod that is edefined on the invoice.\n- Table for invoices\n  - `creditcard_invoices_main`\n  - `creditcard_invoice_items`\n- Match each invoice line item with receipts having the same `purchase_date` and amount\n- If there is a check set true in unified_files_credit_card_match\n\n```\nYou are an AI model responsible for reconciling credit card invoices with receipts.  \n\nInput:\n- A credit card invoice, stored in tables:\n  - creditcard_invoices_main (invoice header, metadata)\n  - creditcard_invoice_items (each transaction line with date, amount, merchant)\n- Receipts stored in unified_files (file_type=\'receipt\') and related tables.  \n\nYour task:\n1. For each row in creditcard_invoice_items, find the best matching receipt(s) from unified_files.  \n   - Match primarily on purchase_date and amount.  \n   - Secondary criteria: merchant_name similarity.  \n   - If multiple candidates exist, pick the one with the closest match in both amount and date.  \n\n2. Output your results in JSON format, one object per invoice line:\n   {\n     \"invoice_item_id\": \"...\",\n     \"receipt_id\": \"...\",\n     \"match\": true/false,\n     \"match_score\": 0.0–1.0,\n     \"notes\": \"explanation of why it matched or not\"\n   }\n\n3. If a match is found, set the field unified_files.credit_card_match = true for that receipt.  \n\nRules:\n- Match must be exact or very close (date difference max ±1 day, amount difference max ±1 SEK unless otherwise stated).  \n- If no good match is found, return \"match\": false.  \n- Always ensure consistent reconciliation (one receipt should not be matched to multiple invoice lines unless explicitly marked as split).  \n\n```\n\n', 1, '2025-09-30 12:08:56', '2025-10-03 06:18:03'),
(6, 'data_extraction', 'AI3: Data Extraction', 'Extract structured data from receipts', 'AI3: You are a deterministic data extractor for Swedish receipts and invoices.\nYour only goal is to parse OCR text into database-ready JSON for: companies, unified_files, and receipt_items.\n\nCRITICAL: Extract the COMPANY NAME from the TOP of the receipt - NOT from amount lines!\n\n- The company name is usually the FIRST line or near the top\n- NEVER use lines containing \"SUMMA\", \"TOTAL\", \"BELOPP\", \"ATT BETALA\" as company name\n- NEVER use amount lines (lines with prices like \"123.45\") as company name\n\nReturn JSON with this structure:\n{\n  \"company\": {\n    \"name\": \"Company Name Here\",\n    \"orgnr\": \"Organization number if found\",\n    \"address\": \"Street address\",\n    \"zip\": \"Postal code\",\n    \"city\": \"City name\",\n    \"country\": \"Country (default Sweden if not stated)\",\n    \"phone\": \"Phone number if present\",\n    \"www\": \"Website if present\"\n  },\n  \"unified_file\": {\n    \"purchase_datetime\": \"2025-09-30T14:23:00 or null\",\n    \"payment_type\": \"card or cash\",\n    \"currency\": \"SEK or other ISO code\",\n    \"gross_amount_original\": 123.45,\n    \"net_amount_original\": 98.76,\n    \"exchange_rate\": 0 for SEK, or bps for foreign,\n    \"gross_amount_sek\": 123,\n    \"net_amount_sek\": 99,\n    \"receipt_number\": \"Receipt number if found\",\n    \"other_data\": \"{\"terminal\":\"123\",\"aid\":\"A000\"}\"\n  },\n  \"receipt_items\": [\n    {\n      \"main_id\": \"file_id\",\n      \"article_id\": \"\",\n      \"name\": \"Product name\",\n      \"number\": 1,\n      \"item_price_ex_vat\": 10.00,\n      \"item_price_inc_vat\": 12.50,\n      \"item_total_price_ex_vat\": 10.00,\n      \"item_total_price_inc_vat\": 12.50,\n      \"currency\": \"SEK\",\n      \"vat\": 2.50,\n      \"vat_percentage\": 0.250000\n    }\n  ],\n  \"confidence\": 0.85\n}\n\nRules:\n- Dates: ISO format YYYY-MM-DD HH:MM:SS, use 00:00:00 if time missing\n- Numbers: Accept , or . as decimal, normalize to .\n- VAT math: net = gross / (1 + rate), vat = gross - net\n- SEK amounts: Round to whole kronor (no decimals)\n- Currency SEK: exchange_rate=0\n- Foreign currency: multiply rate by 100 for exchange_rate (e.g. 11.33 â†’ 1133)\n- NEVER invent data - if unsure, use null\n- Banks are not merhants or shops. Handelsbanken, Nordea, Swedbank and other banks are not shops. \n- Organization number might be \"Org.Nr\" or \"Organisationsnummer\" or similar. The format is always XXXXXX-YYYY ', 1, '2025-10-01 17:58:23', '2025-10-03 06:17:06'),
(7, 'document_analysis', 'AI1: Document Classification', 'Classify document type', 'AI 1: \"You are an AI model receiving text from a scanned document.\nDetermine the document type: \"receipt\", \"invoice\", or \"other\".\nFocus on text clues (e.g., words like \"KVITTO\", \"FAKTURA\", \"VAT\", company names, reference numbers).\nRespond with ONLY one of these three labels without explanation ', 1, '2025-10-01 17:58:23', '2025-10-03 06:17:38'),
(8, 'expense_classification', 'AI2: Expense Classification', 'Classify personal vs corporate expense', ' AI2: You are an AI model analyzing receipt details (payment method, card data, contextual text).\nDetermine whether the receipt is an *employee expense* or a *company card expense*.\nLook for signs such as company card names, \"FirstCard\", \"MasterCard\", or if payment is linked to employee.\nReply with either \"personal\" or \"corporate\" only, without any extra text.', 1, '2025-10-01 17:58:23', '2025-10-03 06:17:06');

-- --------------------------------------------------------

--
-- Tabellstruktur `chart_of_accounts`
--

CREATE TABLE `chart_of_accounts` (
  `id` int NOT NULL,
  `main_account` varchar(10) DEFAULT NULL,
  `main_account_description` varchar(255) DEFAULT NULL,
  `no_k2` tinyint(1) DEFAULT NULL,
  `simple_account` varchar(10) DEFAULT NULL,
  `sub_account` varchar(10) DEFAULT NULL,
  `sub_account_description` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `chart_of_accounts`
--

INSERT INTO `chart_of_accounts` (`id`, `main_account`, `main_account_description`, `no_k2`, `simple_account`, `sub_account`, `sub_account_description`) VALUES
(1, '1', 'Tillgångar', NULL, NULL, NULL, NULL),
(2, '10', 'Immateriella anläggningstillgångar', NULL, NULL, NULL, NULL),
(3, '101', 'Utvecklingsutgifter', 1, NULL, '1010', 'Utvecklingsutgifter'),
(4, '101', 'Utvecklingsutgifter', 1, NULL, '1011', 'Balanserade utgifter för forskning och utveckling'),
(5, '101', 'Utvecklingsutgifter', 1, NULL, '1012', 'Balanserade utgifter för programvaror'),
(6, '101', 'Utvecklingsutgifter', 1, NULL, '1018', 'Ackumulerade nedskrivningar på balanserade utgifter'),
(7, '101', 'Utvecklingsutgifter', 1, NULL, '1019', 'Ackumulerade avskrivningar på balanserade utgifter'),
(8, '102', 'Koncessioner m.m.', NULL, NULL, '1020', 'Koncessioner m.m.'),
(9, '102', 'Koncessioner m.m.', NULL, NULL, '1028', 'Ackumulerade nedskrivningar på koncessioner m.m.'),
(10, '102', 'Koncessioner m.m.', NULL, NULL, '1029', 'Ackumulerade avskrivningar på koncessioner m.m.'),
(11, '103', 'Patent', NULL, '1', '1030', 'Patent'),
(12, '103', 'Patent', NULL, NULL, '1038', 'Ackumulerade nedskrivningar på patent'),
(13, '103', 'Patent', NULL, '1', '1039', 'Ackumulerade avskrivningar på patent'),
(14, '104', 'Licenser', NULL, NULL, '1040', 'Licenser'),
(15, '104', 'Licenser', NULL, NULL, '1048', 'Ackumulerade nedskrivningar på licenser'),
(16, '104', 'Licenser', NULL, NULL, '1049', 'Ackumulerade avskrivningar på licenser'),
(17, '105', 'Varumärken', NULL, NULL, '1050', 'Varumärken'),
(18, '105', 'Varumärken', NULL, NULL, '1058', 'Ackumulerade nedskrivningar på varumärken'),
(19, '105', 'Varumärken', NULL, NULL, '1059', 'Ackumulerade avskrivningar på varumärken'),
(20, '106', 'Hyresrätter, tomträtter och liknande', NULL, '1', '1060', 'Hyresrätter, tomträtter och liknande'),
(21, '106', 'Hyresrätter, tomträtter och liknande', NULL, NULL, '1068', 'Ackumulerade nedskrivningar på hyresrätter, tomträtter och liknande'),
(22, '106', 'Hyresrätter, tomträtter och liknande', NULL, '1', '1069', 'Ackumulerade avskrivningar på hyresrätter, tomträtter och liknande'),
(23, '107', 'Goodwill', NULL, NULL, '1070', 'Goodwill'),
(24, '107', 'Goodwill', NULL, NULL, '1078', 'Ackumulerade nedskrivningar på goodwill'),
(25, '107', 'Goodwill', NULL, NULL, '1079', 'Ackumulerade avskrivningar på goodwill'),
(26, '108', 'Förskott för immateriella anläggningstillgångar', NULL, NULL, '1080', 'Förskott för immateriella anläggningstillgångar'),
(27, '108', 'Förskott för immateriella anläggningstillgångar', 1, NULL, '1081', 'Pågående projekt för immateriella anläggningstillgångar'),
(28, '108', 'Förskott för immateriella anläggningstillgångar', NULL, NULL, '1088', 'Förskott för immateriella anläggningstillgångar'),
(29, '11', 'Byggnader och mark', NULL, NULL, NULL, NULL),
(30, '111', 'Byggnader', NULL, '1', '1110', 'Byggnader'),
(31, '111', 'Byggnader', NULL, NULL, '1111', 'Byggnader på egen mark'),
(32, '111', 'Byggnader', NULL, NULL, '1112', 'Byggnader på annans mark'),
(33, NULL, 'Byggnader', NULL, NULL, '1118', 'Ackumulerade nedskrivningar på byggnader'),
(34, NULL, 'Byggnader', NULL, '1', '1119', 'Ackumulerade avskrivningar på byggnader'),
(35, '112', 'Förbättringsutgifter på annans fastighet', NULL, NULL, '1120', 'Förbättringsutgifter på annans fastighet'),
(36, NULL, 'Förbättringsutgifter på annans fastighet', NULL, NULL, '1129', 'Ackumulerade avskrivningar på förbättringsutgifter på annans fastighet'),
(37, '113', 'Mark', NULL, '1', '1130', 'Mark'),
(38, '114', 'Tomter och obebyggda markområden', NULL, NULL, '1140', 'Tomter och obebyggda markområden'),
(39, '115', 'Markanläggningar', NULL, '1', '1150', 'Markanläggningar'),
(40, NULL, 'Markanläggningar', NULL, NULL, '1158', 'Ackumulerade nedskrivningar på markanläggningar'),
(41, NULL, 'Markanläggningar', NULL, '1', '1159', 'Ackumulerade avskrivningar på markanläggningar'),
(42, '118', 'Pågående nyanläggningar och förskott för byggnader och mark', NULL, NULL, '1180', 'Pågående nyanläggningar och förskott för byggnader och mark'),
(43, NULL, 'Pågående nyanläggningar och förskott för byggnader och mark', NULL, NULL, '1181', 'Pågående ny-, till- och ombyggnad'),
(44, NULL, 'Pågående nyanläggningar och förskott för byggnader och mark', NULL, NULL, '1188', 'Förskott för byggnader och mark'),
(45, '12', 'Maskiner och inventarier', NULL, NULL, NULL, NULL),
(46, '121', 'Maskiner och andra tekniska anläggningar', NULL, '1', '1210', 'Maskiner och andra tekniska anläggningar'),
(47, NULL, 'Maskiner och andra tekniska anläggningar', NULL, NULL, '1211', 'Maskiner'),
(48, NULL, 'Maskiner och andra tekniska anläggningar', NULL, NULL, '1213', 'Andra tekniska anläggningar'),
(49, NULL, 'Maskiner och andra tekniska anläggningar', NULL, NULL, '1218', 'Ackumulerade nedskrivningar på maskiner och andra tekniska anläggningar'),
(50, NULL, 'Maskiner och andra tekniska anläggningar', NULL, '1', '1219', 'Ackumulerade avskrivningar på maskiner och andra tekniska anläggningar'),
(51, '122', 'Inventarier och verktyg', NULL, '1', '1220', 'Inventarier och verktyg'),
(52, NULL, 'Inventarier och verktyg', NULL, NULL, '1221', 'Inventarier'),
(53, NULL, 'Inventarier och verktyg', NULL, NULL, '1222', 'Byggnadsinventarier'),
(54, NULL, 'Inventarier och verktyg', NULL, NULL, '1223', 'Markinventarier'),
(55, NULL, 'Inventarier och verktyg', NULL, NULL, '1225', 'Verktyg'),
(56, NULL, 'Inventarier och verktyg', NULL, NULL, '1228', 'Ackumulerade nedskrivningar på inventarier och verktyg'),
(57, NULL, 'Inventarier och verktyg', NULL, '1', '1229', 'Ackumulerade avskrivningar på inventarier och verktyg'),
(58, '123', 'Installationer', NULL, NULL, '1230', 'Installationer'),
(59, NULL, 'Installationer', NULL, NULL, '1231', 'Installationer på egen fastighet'),
(60, NULL, 'Installationer', NULL, NULL, '1232', 'Installationer på annans fastighet'),
(61, NULL, 'Installationer', NULL, NULL, '1238', 'Ackumulerade nedskrivningar på installationer'),
(62, NULL, 'Installationer', NULL, NULL, '1239', 'Ackumulerade avskrivningar på installationer'),
(63, '124', 'Bilar och andra transportmedel', NULL, '1', '1240', 'Bilar och andra transportmedel'),
(64, NULL, 'Bilar och andra transportmedel', NULL, NULL, '1241', 'Personbilar'),
(65, NULL, 'Bilar och andra transportmedel', NULL, NULL, '1242', 'Lastbilar'),
(66, NULL, 'Bilar och andra transportmedel', NULL, NULL, '1243', 'Truckar'),
(67, NULL, 'Bilar och andra transportmedel', NULL, NULL, '1244', 'Arbetsmaskiner'),
(68, NULL, 'Bilar och andra transportmedel', NULL, NULL, '1245', 'Traktorer'),
(69, NULL, 'Bilar och andra transportmedel', NULL, NULL, '1246', 'Motorcyklar, mopeder och skotrar'),
(70, NULL, 'Bilar och andra transportmedel', NULL, NULL, '1247', 'Båtar, flygplan och helikoptrar'),
(71, NULL, 'Bilar och andra transportmedel', NULL, NULL, '1248', 'Ackumulerade nedskrivningar på bilar och andra transportmedel'),
(72, NULL, 'Bilar och andra transportmedel', NULL, '1', '1249', 'Ackumulerade avskrivningar på bilar och andra transportmedel'),
(73, '125', 'Datorer', NULL, '1', '1250', 'Datorer'),
(74, NULL, 'Datorer', NULL, NULL, '1251', 'Datorer, företaget'),
(75, NULL, 'Datorer', NULL, NULL, '1257', 'Datorer, personal'),
(76, NULL, 'Datorer', NULL, NULL, '1258', 'Ackumulerade nedskrivningar på datorer'),
(77, NULL, 'Datorer', NULL, '1', '1259', 'Ackumulerade avskrivningar på datorer'),
(78, '126', 'Leasade tillgångar', 1, NULL, '1260', 'Leasade tillgångar'),
(79, NULL, 'Leasade tillgångar', 1, NULL, '1269', 'Ackumulerade avskrivningar på leasade tillgångar'),
(80, '128', 'Pågående nyanläggningar och förskott för maskiner och inventarier', NULL, NULL, '1280', 'Pågående nyanläggningar och förskott för maskiner och inventarier'),
(81, NULL, 'Pågående nyanläggningar och förskott för maskiner och inventarier', NULL, NULL, '1281', 'Pågående nyanläggningar, maskiner och inventarier'),
(82, NULL, 'Pågående nyanläggningar och förskott för maskiner och inventarier', NULL, NULL, '1288', 'Förskott för maskiner och inventarier'),
(83, '129', 'Övriga materiella anläggningstillgångar', NULL, '1', '1290', 'Övriga materiella anläggningstillgångar'),
(84, NULL, 'Övriga materiella anläggningstillgångar', NULL, '1', '1291', 'Konst och liknande tillgångar'),
(85, NULL, 'Övriga materiella anläggningstillgångar', NULL, NULL, '1292', 'Djur som klassificeras som anläggningstillgång'),
(86, NULL, 'Övriga materiella anläggningstillgångar', NULL, NULL, '1298', 'Ackumulerade nedskrivningar på övriga materiella anläggningstillgångar'),
(87, NULL, 'Övriga materiella anläggningstillgångar', NULL, '1', '1299', 'Ackumulerade avskrivningar på övriga materiella anläggningstillgångar'),
(88, '13', 'Finansiella anläggningstillgångar', NULL, NULL, NULL, NULL),
(89, '131', 'Andelar i koncernföretag', NULL, NULL, '1310', 'Andelar i koncernföretag'),
(90, NULL, 'Andelar i koncernföretag', NULL, NULL, '1311', 'Aktier i noterade svenska koncernföretag'),
(91, NULL, 'Andelar i koncernföretag', NULL, NULL, '1312', 'Aktier i onoterade svenska koncernföretag'),
(92, NULL, 'Andelar i koncernföretag', NULL, NULL, '1313', 'Aktier i noterade utländska koncernföretag'),
(93, NULL, 'Andelar i koncernföretag', NULL, NULL, '1314', 'Aktier i onoterade utländska koncernföretag'),
(94, NULL, 'Andelar i koncernföretag', NULL, NULL, '1316', 'Andra andelar i svenska koncernföretag'),
(95, NULL, 'Andelar i koncernföretag', NULL, NULL, '1317', 'Andra andelar i utländska koncernförertag'),
(96, NULL, 'Andelar i koncernföretag', NULL, NULL, '1318', 'Ackumulerade nedskrivningar av andelar i koncernföretag'),
(97, '132', 'Långfristiga fordringar hos koncernföretag', NULL, NULL, '1320', 'Långfristiga fordringar hos koncernföretag'),
(98, NULL, 'Långfristiga fordringar hos koncernföretag', NULL, NULL, '1321', 'Långfristiga fordringar hos moderföretag'),
(99, NULL, 'Långfristiga fordringar hos koncernföretag', NULL, NULL, '1322', 'Långfristiga fordringar hos dotterföretag'),
(100, NULL, 'Långfristiga fordringar hos koncernföretag', NULL, NULL, '1323', 'Långfristiga fordringar hos andra koncernföretag'),
(101, NULL, 'Långfristiga fordringar hos koncernföretag', NULL, NULL, '1328', 'Ackumulerade nedskrivningar av långfristiga fordringar hos koncernföretag'),
(102, '133', 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1330', 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(103, NULL, 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1331', 'Andelar i intresseföretag'),
(104, NULL, 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1332', 'Ackumulerade nedskrivningar av andelar i intresseföretag'),
(105, NULL, 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1333', 'Andelar i gemensamt styrda företag'),
(106, NULL, 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1334', 'Ackumulerade nedskrivningar av andelar i gemensamt styrda företag'),
(107, NULL, 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1336', 'Andelar i övriga företag som det finns ett ägarintresse i'),
(108, NULL, 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1337', 'Ackumulerade nedskrivningar av andelar i övriga företag som det finns ett ägarintresse i'),
(109, NULL, 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1338', 'Ackumulerade nedskrivningar av andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(110, '134', 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1340', 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(111, NULL, 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1341', 'Långfristiga fordringar hos intresseföretag'),
(112, NULL, 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1342', 'Ackumulerade nedskrivningar av långfristiga fordringar hos intresseföretag'),
(113, NULL, 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1343', 'Långfristiga fordringar hos gemensamt styrda företag'),
(114, NULL, 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1344', 'Ackumulerade nedskrivningar av långfristiga fordringar hos gemensamt styrda företag'),
(115, NULL, 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1346', 'Långfristiga fordringar hos övriga företag som det finns ett ägarintresse i'),
(116, NULL, 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1347', 'Ackumulerade nedskrivningar av långfristiga fordringar hos övriga företag som det finns ett ägarintresse i'),
(117, NULL, 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1348', 'Ackumulerade nedskrivningar av långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(118, '135', 'Andelar och värdepapper i andra företag', NULL, '1', '1350', 'Andelar och värdepapper i andra företag'),
(119, NULL, 'Andelar och värdepapper i andra företag', NULL, NULL, '1351', 'Andelar i noterade företag'),
(120, NULL, 'Andelar och värdepapper i andra företag', NULL, NULL, '1352', 'Andra andelar'),
(121, NULL, 'Andelar och värdepapper i andra företag', NULL, NULL, '1353', 'Andelar i bostadsrättsföreningar'),
(122, NULL, 'Andelar och värdepapper i andra företag', NULL, NULL, '1354', 'Obligationer'),
(123, NULL, 'Andelar och värdepapper i andra företag', NULL, NULL, '1356', 'Andelar i ekonomiska föreningar, övriga företag'),
(124, NULL, 'Andelar och värdepapper i andra företag', NULL, NULL, '1357', 'Andelar i handelsbolag, andra företag'),
(125, NULL, 'Andelar och värdepapper i andra företag', NULL, NULL, '1358', 'Ackumulerade nedskrivningar av andra andelar och värdepapper'),
(126, '136', 'Lån till delägare eller närstående, långfristig del', NULL, NULL, '1360', 'Lån till delägare eller närstående, långfristig del'),
(127, NULL, 'Lån till delägare eller närstående, långfristig del', NULL, NULL, '1369', 'Ackumulerade nedskrivningar av lån till delägare eller närstående, långfristig del'),
(128, '137', 'Uppskjuten skattefordran', 1, NULL, '1370', 'Uppskjuten skattefordran'),
(129, '138', 'Andra långfristiga fordringar', NULL, '1', '1380', 'Andra långfristiga fordringar'),
(130, NULL, 'Andra långfristiga fordringar', NULL, NULL, '1381', 'Långfristiga reversfordringar'),
(131, NULL, 'Andra långfristiga fordringar', NULL, NULL, '1382', 'Långfristiga fordringar hos anställda'),
(132, NULL, 'Andra långfristiga fordringar', NULL, NULL, '1383', 'Lämnade depositioner, långfristiga'),
(133, NULL, 'Andra långfristiga fordringar', NULL, NULL, '1384', 'Derivat'),
(134, NULL, 'Andra långfristiga fordringar', NULL, NULL, '1385', 'Kapitalförsäkring'),
(135, NULL, 'Andra långfristiga fordringar', NULL, NULL, '1387', 'Långfristiga kontraktsfordringar'),
(136, NULL, 'Andra långfristiga fordringar', NULL, NULL, '1388', 'Långfristiga kundfordringar'),
(137, NULL, 'Andra långfristiga fordringar', NULL, NULL, '1389', 'Ackumulerade nedskrivningar av andra långfristiga fordringar'),
(138, '14', 'Lager, produkter i arbete och pågående arbeten', NULL, NULL, NULL, NULL),
(139, '141', 'Lager av råvaror', NULL, '1', '1410', 'Lager av råvaror'),
(140, NULL, 'Lager av råvaror', NULL, '1', '1419', 'Förändring av lager av råvaror'),
(141, '142', 'Lager av tillsatsmaterial och förnödenheter', NULL, NULL, '1420', 'Lager av tillsatsmaterial och förnödenheter'),
(142, NULL, 'Lager av tillsatsmaterial och förnödenheter', NULL, NULL, '1429', 'Förändring av lager av tillsatsmaterial och förnödenheter'),
(143, '144', 'Produkter i arbete', NULL, '1', '1440', 'Produkter i arbete'),
(144, NULL, 'Produkter i arbete', NULL, '1', '1449', 'Förändring av produkter i arbete'),
(145, '145', 'Lager av färdiga varor', NULL, '1', '1450', 'Lager av färdiga varor'),
(146, NULL, 'Lager av färdiga varor', NULL, '1', '1459', 'Förändring av lager av färdiga varor'),
(147, '146', 'Lager av handelsvaror', NULL, '1', '1460', 'Lager av handelsvaror'),
(148, NULL, 'Lager av handelsvaror', NULL, NULL, '1465', 'Lager av varor VMB'),
(149, NULL, 'Lager av handelsvaror', NULL, NULL, '1466', 'Nedskrivning av varor VMB'),
(150, NULL, 'Lager av handelsvaror', NULL, NULL, '1467', 'Lager av varor VMB förenklad'),
(151, NULL, 'Lager av handelsvaror', NULL, '1', '1469', 'Förändring av lager av handelsvaror'),
(152, '147', 'Pågående arbeten', NULL, '1', '1470', 'Pågående arbeten'),
(153, NULL, 'Pågående arbeten', NULL, NULL, '1471', 'Pågående arbeten, nedlagda kostnader'),
(154, NULL, 'Pågående arbeten', NULL, NULL, '1478', 'Pågående arbeten, fakturering'),
(155, NULL, 'Pågående arbeten', NULL, '1', '1479', 'Förändring av pågående arbeten'),
(156, '148', 'Förskott för varor och tjänster', NULL, '1', '1480', 'Förskott för varor och tjänster'),
(157, NULL, 'Förskott för varor och tjänster', NULL, NULL, '1481', 'Remburser'),
(158, NULL, 'Förskott för varor och tjänster', NULL, NULL, '1489', 'Övriga förskott till leverantörer'),
(159, '149', 'Övriga lagertillgångar', NULL, '1', '1490', 'Övriga lagertillgångar'),
(160, NULL, 'Övriga lagertillgångar', NULL, NULL, '1491', 'Lager av värdepapper'),
(161, NULL, 'Övriga lagertillgångar', NULL, NULL, '1492', 'Lager av fastigheter'),
(162, NULL, 'Övriga lagertillgångar', NULL, NULL, '1493', 'Djur som klassificeras som omsättningstillgång'),
(163, '15', 'Kundfordringar', NULL, NULL, NULL, NULL),
(164, '151', 'Kundfordringar', NULL, '1', '1510', 'Kundfordringar'),
(165, NULL, 'Kundfordringar', NULL, NULL, '1511', 'Kundfordringar'),
(166, NULL, 'Kundfordringar', NULL, NULL, '1512', 'Belånade kundfordringar (factoring)'),
(167, NULL, 'Kundfordringar', NULL, '1', '1513', 'Kundfordringar – delad faktura'),
(168, NULL, 'Kundfordringar', NULL, NULL, '1516', 'Tvistiga kundfordringar'),
(169, NULL, 'Kundfordringar', 1, NULL, '1518', 'Ej reskontraförda kundfordringar'),
(170, NULL, 'Kundfordringar', NULL, '1', '1519', 'Nedskrivning av kundfordringar'),
(171, '152', 'Växelfordringar', NULL, NULL, '1520', 'Växelfordringar'),
(172, NULL, 'Växelfordringar', NULL, NULL, '1525', 'Osäkra växelfordringar'),
(173, NULL, 'Växelfordringar', NULL, NULL, '1529', 'Nedskrivning av växelfordringar'),
(174, '153', 'Kontraktsfordringar', NULL, NULL, '1530', 'Kontraktsfordringar'),
(175, NULL, 'Kontraktsfordringar', NULL, NULL, '1531', 'Kontraktsfordringar'),
(176, NULL, 'Kontraktsfordringar', NULL, NULL, '1532', 'Belånade kontraktsfordringar'),
(177, NULL, 'Kontraktsfordringar', NULL, NULL, '1536', 'Tvistiga kontraktsfordringar'),
(178, NULL, 'Kontraktsfordringar', NULL, NULL, '1539', 'Nedskrivning av kontraktsfordringar'),
(179, '155', 'Konsignationsfordringar', NULL, NULL, '1550', 'Konsignationsfordringar'),
(180, '156', 'Kundfordringar hos koncernföretag', NULL, NULL, '1560', 'Kundfordringar hos koncernföretag'),
(181, NULL, 'Kundfordringar hos koncernföretag', NULL, NULL, '1561', 'Kundfordringar hos moderföretag'),
(182, NULL, 'Kundfordringar hos koncernföretag', NULL, NULL, '1562', 'Kundfordringar hos dotterföretag'),
(183, NULL, 'Kundfordringar hos koncernföretag', NULL, NULL, '1563', 'Kundfordringar hos andra koncernföretag'),
(184, NULL, 'Kundfordringar hos koncernföretag', NULL, NULL, '1568', 'Ej reskontraförda kundfordringar hos koncernföretag'),
(185, NULL, 'Kundfordringar hos koncernföretag', NULL, NULL, '1569', 'Nedskrivning av kundfordringar hos koncernföretag'),
(186, '157', 'Kundfordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1570', 'Kundfordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(187, NULL, 'Kundfordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1571', 'Kundfordringar hos intresseföretag'),
(188, NULL, 'Kundfordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1572', 'Kundfordringar hos gemensamt styrda företag'),
(189, NULL, 'Kundfordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1573', 'Kundfordringar hos övriga företag som det finns ett ägarintresse i'),
(190, '158', 'Fordringar för kontokort och kuponger', NULL, '1', '1580', 'Fordringar för kontokort och kuponger'),
(191, '16', 'Övriga kortfristiga fordringar', NULL, NULL, NULL, NULL),
(192, '161', 'Kortfristiga fordringar hos anställda', NULL, '1', '1610', 'Kortfristiga fordringar hos anställda'),
(193, NULL, 'Kortfristiga fordringar hos anställda', NULL, NULL, '1611', 'Reseförskott'),
(194, NULL, 'Kortfristiga fordringar hos anställda', NULL, NULL, '1612', 'Kassaförskott'),
(195, NULL, 'Kortfristiga fordringar hos anställda', NULL, NULL, '1613', 'Övriga förskott'),
(196, NULL, 'Kortfristiga fordringar hos anställda', NULL, NULL, '1614', 'Tillfälliga lån till anställda'),
(197, NULL, 'Kortfristiga fordringar hos anställda', NULL, NULL, '1619', 'Övriga fordringar hos anställda'),
(198, '162', 'Upparbetad men ej fakturerad intäkt', NULL, NULL, '1620', 'Upparbetad men ej fakturerad intäkt'),
(199, '163', 'Avräkning för skatter och avgifter (skattekonto)', NULL, '1', '1630', 'Avräkning för skatter och avgifter (skattekonto)'),
(200, '164', 'Skattefordringar', NULL, '1', '1640', 'Skattefordringar'),
(201, '165', 'Momsfordran', NULL, '1', '1650', 'Momsfordran'),
(202, '166', 'Kortfristiga fordringar hos koncernföretag', NULL, NULL, '1660', 'Kortfristiga fordringar hos koncernföretag'),
(203, NULL, 'Kortfristiga fordringar hos koncernföretag', NULL, NULL, '1661', 'Kortfristiga fordringar hos moderföretag'),
(204, NULL, 'Kortfristiga fordringar hos koncernföretag', NULL, NULL, '1662', 'Kortfristiga fordringar hos dotterföretag'),
(205, NULL, 'Kortfristiga fordringar hos koncernföretag', NULL, NULL, '1663', 'Kortfristiga fordringar hos andra koncernföretag'),
(206, '167', 'Kortfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1670', 'Kortfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(207, NULL, 'Kortfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1671', 'Kortfristiga fordringar hos intresseföretag'),
(208, NULL, 'Kortfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1672', 'Kortfristiga fordringar hos gemensamt styrda företag'),
(209, NULL, 'Kortfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '1673', 'Kortfristiga fordringar hos övriga företag som det finns ett ägarintresse i'),
(210, '168', 'Andra kortfristiga fordringar', NULL, '1', '1680', 'Andra kortfristiga fordringar'),
(211, NULL, 'Andra kortfristiga fordringar', NULL, NULL, '1681', 'Utlägg för kunder'),
(212, NULL, 'Andra kortfristiga fordringar', NULL, NULL, '1682', 'Kortfristiga lånefordringar'),
(213, NULL, 'Andra kortfristiga fordringar', NULL, NULL, '1683', 'Derivat'),
(214, NULL, 'Andra kortfristiga fordringar', NULL, NULL, '1684', 'Kortfristiga fordringar hos leverantörer'),
(215, NULL, 'Andra kortfristiga fordringar', NULL, NULL, '1685', 'Kortfristiga fordringar hos delägare eller närstående'),
(216, NULL, 'Andra kortfristiga fordringar', NULL, NULL, '1687', 'Kortfristig del av långfristiga fordringar'),
(217, NULL, 'Andra kortfristiga fordringar', NULL, NULL, '1688', 'Fordran arbetsmarknadsförsäkringar'),
(218, NULL, 'Andra kortfristiga fordringar', NULL, NULL, '1689', 'Övriga kortfristiga fordringar'),
(219, '169', 'Fordringar för tecknat men ej inbetalt aktiekapital', NULL, NULL, '1690', 'Fordringar för tecknat men ej inbetalt aktiekapital'),
(220, '17', 'Förutbetalda kostnader och upplupna intäkter', NULL, NULL, NULL, NULL),
(221, '171', 'Förutbetalda hyreskostnader', NULL, '1', '1710', 'Förutbetalda hyreskostnader'),
(222, '172', 'Förutbetalda leasingavgifter', NULL, '1', '1720', 'Förutbetalda leasingavgifter'),
(223, '173', 'Förutbetalda försäkringspremier', NULL, '1', '1730', 'Förutbetalda försäkringspremier'),
(224, '174', 'Förutbetalda räntekostnader', NULL, '1', '1740', 'Förutbetalda räntekostnader'),
(225, '175', 'Upplupna hyresintäkter', NULL, '1', '1750', 'Upplupna hyresintäkter'),
(226, '176', 'Upplupna ränteintäkter', NULL, '1', '1760', 'Upplupna ränteintäkter'),
(227, '177', 'Tillgångar av kostnadsnatur', NULL, NULL, '1770', 'Tillgångar av kostnadsnatur'),
(228, '178', 'Upplupna avtalsintäkter', NULL, NULL, '1780', 'Upplupna avtalsintäkter'),
(229, '179', 'Övriga förutbetalda kostnader och upplupna intäkter', NULL, '1', '1790', 'Övriga förutbetalda kostnader och upplupna intäkter'),
(230, '18', 'Kortfristiga placeringar', NULL, NULL, NULL, NULL),
(231, '181', 'Andelar i börsnoterade företag', NULL, '1', '1810', 'Andelar i börsnoterade företag'),
(232, '182', 'Obligationer', NULL, NULL, '1820', 'Obligationer'),
(233, '183', 'Konvertibla skuldebrev', NULL, NULL, '1830', 'Konvertibla skuldebrev'),
(234, '186', 'Andelar i koncernföretag, kortfristigt', NULL, NULL, '1860', 'Andelar i koncernföretag, kortfristigt'),
(235, '188', 'Andra kortfristiga placeringar', NULL, '1', '1880', 'Andra kortfristiga placeringar'),
(236, NULL, 'Andra kortfristiga placeringar', NULL, NULL, '1886', 'Derivat'),
(237, NULL, 'Andra kortfristiga placeringar', NULL, NULL, '1889', 'Andelar i övriga företag'),
(238, '189', 'Nedskrivning av kortfristiga placeringar', NULL, '1', '1890', 'Nedskrivning av kortfristiga placeringar'),
(239, '19', 'Kassa och bank', NULL, NULL, NULL, NULL),
(240, '191', 'Kassa', NULL, '1', '1910', 'Kassa'),
(241, NULL, 'Kassa', NULL, NULL, '1911', 'Huvudkassa'),
(242, NULL, 'Kassa', NULL, NULL, '1912', 'Kassa 2'),
(243, NULL, 'Kassa', NULL, NULL, '1913', 'Kassa 3'),
(244, '192', 'PlusGiro', NULL, '1', '1920', 'PlusGiro'),
(245, '193', 'Företagskonto/checkkonto/affärskonto', NULL, '1', '1930', 'Företagskonto/checkkonto/affärskonto'),
(246, '194', 'Övriga bankkonton', NULL, '1', '1940', 'Övriga bankkonton'),
(247, '195', 'Bankcertifikat', NULL, NULL, '1950', 'Bankcertifikat'),
(248, '196', 'Koncernkonto moderföretag', NULL, NULL, '1960', 'Koncernkonto moderföretag'),
(249, '197', 'Särskilda bankkonton', NULL, NULL, '1970', 'Särskilda bankkonton'),
(250, NULL, 'Särskilda bankkonton', NULL, NULL, '1972', 'Upphovsmannakonto'),
(251, NULL, 'Särskilda bankkonton', NULL, NULL, '1973', 'Skogskonto'),
(252, NULL, 'Särskilda bankkonton', NULL, NULL, '1974', 'Spärrade bankmedel'),
(253, NULL, 'Särskilda bankkonton', NULL, NULL, '1979', 'Övriga särskilda bankkonton'),
(254, '198', 'Valutakonton', NULL, NULL, '1980', 'Valutakonton'),
(255, '199', 'Redovisningsmedel', NULL, NULL, '1990', 'Redovisningsmedel'),
(256, '2', 'Eget kapital och skulder', NULL, NULL, NULL, NULL),
(257, '20', 'Eget kapital', NULL, NULL, NULL, NULL),
(258, '201', 'Eget kapital (enskild firma)', NULL, '1', '2010', 'Eget kapital'),
(259, NULL, 'Eget kapital (enskild firma)', NULL, '1', '2011', 'Egna varuuttag'),
(260, NULL, 'Eget kapital (enskild firma)', NULL, '1', '2013', 'Övriga egna uttag'),
(261, NULL, 'Eget kapital (enskild firma)', NULL, '1', '2017', 'Årets kapitaltillskott'),
(262, NULL, 'Eget kapital (enskild firma)', NULL, '1', '2018', 'Övriga egna insättningar'),
(263, NULL, 'Eget kapital (enskild firma)', NULL, '1', '2019', 'Årets resultat'),
(264, '201', 'Eget kapital, delägare 1', NULL, '1', '2010', 'Eget kapital'),
(265, NULL, 'Eget kapital, delägare 1', NULL, '1', '2011', 'Egna varuuttag'),
(266, NULL, 'Eget kapital, delägare 1', NULL, '1', '2013', 'Övriga egna uttag'),
(267, NULL, 'Eget kapital, delägare 1', NULL, '1', '2017', 'Årets kapitaltillskott'),
(268, NULL, 'Eget kapital, delägare 1', NULL, '1', '2018', 'Övriga egna insättningar'),
(269, NULL, 'Eget kapital, delägare 1', NULL, '1', '2019', 'Årets resultat, delägare 1'),
(270, '202', 'Eget kapital, delägare 2', NULL, '1', '2020', 'Eget kapital'),
(271, NULL, 'Eget kapital, delägare 2', NULL, '1', '2021', 'Egna varuuttag'),
(272, NULL, 'Eget kapital, delägare 2', NULL, '1', '2023', 'Övriga egna uttag'),
(273, NULL, 'Eget kapital, delägare 2', NULL, '1', '2027', 'Årets kapitaltillskott'),
(274, NULL, 'Eget kapital, delägare 2', NULL, '1', '2028', 'Övriga egna insättningar'),
(275, NULL, 'Eget kapital, delägare 2', NULL, '1', '2029', 'Årets resultat, delägare 2'),
(276, '203', 'Eget kapital, delägare 3', NULL, '1', '2030', 'Eget kapital'),
(277, NULL, 'Eget kapital, delägare 3', NULL, '1', '2031', 'Egna varuuttag'),
(278, NULL, 'Eget kapital, delägare 3', NULL, '1', '2033', 'Övriga egna uttag'),
(279, NULL, 'Eget kapital, delägare 3', NULL, '1', '2037', 'Årets kapitaltillskott'),
(280, NULL, 'Eget kapital, delägare 3', NULL, '1', '2038', 'Övriga egna insättningar'),
(281, NULL, 'Eget kapital, delägare 3', NULL, '1', '2039', 'Årets resultat, delägare 3'),
(282, '204', 'Eget kapital, delägare 4', NULL, '1', '2040', 'Eget kapital'),
(283, NULL, 'Eget kapital, delägare 4', NULL, '1', '2041', 'Egna varuuttag'),
(284, NULL, 'Eget kapital, delägare 4', NULL, '1', '2043', 'Övriga egna uttag'),
(285, NULL, 'Eget kapital, delägare 4', NULL, '1', '2047', 'Årets kapitaltillskott'),
(286, NULL, 'Eget kapital, delägare 4', NULL, '1', '2048', 'Övriga egna insättningar'),
(287, NULL, 'Eget kapital, delägare 4', NULL, '1', '2049', 'Årets resultat, delägare 4'),
(288, '205', 'Avsättning till expansionsfond', NULL, NULL, '2050', 'Avsättning till expansionsfond'),
(289, '206', 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', NULL, '1', '2060', 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund'),
(290, NULL, 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', NULL, NULL, '2061', 'Kapital/stiftelsekapital/grundkapital'),
(291, NULL, 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', NULL, NULL, '2064', 'Ackumulerat realisationsresultat'),
(292, NULL, 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', NULL, NULL, '2065', 'Fond för verkligt värde'),
(293, NULL, 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', NULL, NULL, '2066', 'Värdesäkringsfond'),
(294, NULL, 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', NULL, NULL, '2067', 'Balanserat överskott eller underskott'),
(295, NULL, 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', NULL, NULL, '2068', 'Överskott eller underskott från föregående år'),
(296, NULL, 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', NULL, NULL, '2069', 'Årets resultat'),
(297, '207', 'Ändamålsbestämda medel', NULL, '1', '2070', 'Ändamålsbestämda medel'),
(298, NULL, 'Ändamålsbestämda medel', NULL, NULL, '2071', 'Ändamål 1'),
(299, NULL, 'Ändamålsbestämda medel', NULL, NULL, '2072', 'Ändamål 2'),
(300, '208', 'Bundet eget kapital', NULL, NULL, '2080', 'Bundet eget kapital'),
(301, NULL, 'Bundet eget kapital', NULL, '1', '2081', 'Aktiekapital'),
(302, NULL, 'Bundet eget kapital', NULL, NULL, '2082', 'Ej registrerat aktiekapital'),
(303, NULL, 'Bundet eget kapital', NULL, '1', '2083', 'Medlemsinsatser'),
(304, NULL, 'Bundet eget kapital', NULL, NULL, '2084', 'Förlagsinsatser'),
(305, NULL, 'Bundet eget kapital', NULL, NULL, '2085', 'Uppskrivningsfond'),
(306, NULL, 'Bundet eget kapital', NULL, '1', '2086', 'Reservfond'),
(307, NULL, 'Bundet eget kapital', NULL, NULL, '2087', 'Insatsemission'),
(308, NULL, 'Bundet eget kapital', NULL, NULL, '2087', 'Bunden överkursfond'),
(309, NULL, 'Bundet eget kapital', NULL, NULL, '2088', 'Fond för yttre underhåll'),
(310, NULL, 'Bundet eget kapital', 1, NULL, '2089', 'Fond för utvecklingsutgifter'),
(311, '209', 'Fritt eget kapital', NULL, '1', '2090', 'Fritt eget kapital'),
(312, NULL, 'Fritt eget kapital', NULL, '1', '2091', 'Balanserad vinst eller förlust'),
(313, NULL, 'Fritt eget kapital', 1, NULL, '2092', 'Mottagna/lämnade koncernbidrag'),
(314, NULL, 'Fritt eget kapital', NULL, NULL, '2093', 'Erhållna aktieägartillskott'),
(315, NULL, 'Fritt eget kapital', NULL, NULL, '2094', 'Egna aktier'),
(316, NULL, 'Fritt eget kapital', NULL, NULL, '2095', 'Fusionsresultat'),
(317, NULL, 'Fritt eget kapital', 1, NULL, '2096', 'Fond för verkligt värde'),
(318, NULL, 'Fritt eget kapital', NULL, NULL, '2097', 'Fri överkursfond'),
(319, NULL, 'Fritt eget kapital', NULL, '1', '2098', 'Vinst eller förlust från föregående år'),
(320, NULL, 'Fritt eget kapital', NULL, '1', '2099', 'Årets resultat'),
(321, '21', 'Obeskattade reserver', NULL, NULL, NULL, NULL),
(322, '211', 'Periodiseringsfonder', NULL, NULL, '2110', 'Periodiseringsfonder'),
(323, '212', 'Periodiseringsfond 2020', NULL, '1', '2120', 'Periodiseringsfond 2020'),
(324, NULL, 'Periodiseringsfond 2021', NULL, '1', '2121', 'Periodiseringsfond 2021'),
(325, NULL, 'Periodiseringsfond 2022', NULL, '1', '2122', 'Periodiseringsfond 2022'),
(326, NULL, 'Periodiseringsfond 2023', NULL, '1', '2123', 'Periodiseringsfond 2023'),
(327, NULL, 'Periodiseringsfond 2024', NULL, '1', '2124', 'Periodiseringsfond 2024'),
(328, NULL, 'Periodiseringsfond 2025', NULL, '1', '2125', 'Periodiseringsfond 2025'),
(329, NULL, 'Periodiseringsfond 2026', NULL, '1', '2126', 'Periodiseringsfond 2026'),
(330, NULL, 'Periodiseringsfond 2018', NULL, '1', '2128', 'Periodiseringsfond 2018'),
(331, NULL, '2019', NULL, '1', '2129', 'Periodiseringsfond 2019'),
(332, '213', 'Periodiseringsfond 2020 – nr 2', NULL, NULL, '2130', 'Periodiseringsfond 2020 – nr 2'),
(333, NULL, 'Periodiseringsfond 2021 – nr 2', NULL, NULL, '2131', 'Periodiseringsfond 2021 – nr 2'),
(334, NULL, 'Periodiseringsfond 2022 – nr 2', NULL, NULL, '2132', 'Periodiseringsfond 2022 – nr 2'),
(335, NULL, 'Periodiseringsfond 2023 – nr 2', NULL, NULL, '2133', 'Periodiseringsfond 2023 – nr 2'),
(336, NULL, 'Periodiseringsfond 2024 – nr 2', NULL, NULL, '2134', 'Periodiseringsfond 2024 – nr 2'),
(337, NULL, 'Periodiseringsfond 2025 - nr 2', NULL, NULL, '2135', 'Periodiseringsfond 2025 - nr 2'),
(338, NULL, 'Periodiseringsfond 2026 - nr 2', NULL, NULL, '2136', 'Periodiseringsfond 2026 - nr 2'),
(339, NULL, 'Periodiseringsfond 2018 – nr 2', NULL, NULL, '2138', 'Periodiseringsfond 2018 – nr 2'),
(340, NULL, 'Periodiseringsfond 2019 – nr 2', NULL, NULL, '2139', 'Periodiseringsfond 2019 – nr 2'),
(341, '215', 'Ackumulerade överavskrivningar', NULL, '1', '2150', 'Ackumulerade överavskrivningar'),
(342, NULL, 'Ackumulerade överavskrivningar', NULL, NULL, '2151', 'Ackumulerade överavskrivningar på immateriella anläggningstillgångar'),
(343, NULL, 'Ackumulerade överavskrivningar', NULL, NULL, '2152', 'Ackumulerade överavskrivningar på byggnader och markanläggningar'),
(344, NULL, 'Ackumulerade överavskrivningar', NULL, NULL, '2153', 'Ackumulerade överavskrivningar på maskiner och inventarier'),
(345, '216', 'Ersättningsfond', NULL, NULL, '2160', 'Ersättningsfond'),
(346, NULL, 'Ersättningsfond', NULL, NULL, '2161', 'Ersättningsfond maskiner och inventarier'),
(347, NULL, 'Ersättningsfond', NULL, NULL, '2162', 'Ersättningsfond byggnader och markanläggningar'),
(348, NULL, 'Ersättningsfond', NULL, NULL, '2164', 'Ersättningsfond för djurlager i jordbruk och renskötsel'),
(349, '219', 'Övriga obeskattade reserver', NULL, NULL, '2190', 'Övriga obeskattade reserver'),
(350, NULL, 'Övriga obeskattade reserver', NULL, NULL, '2196', 'Lagerreserv'),
(351, NULL, 'Övriga obeskattade reserver', NULL, NULL, '2199', 'Övriga obeskattade reserver'),
(352, '22', 'Avsättningar', NULL, NULL, NULL, NULL),
(353, '221', 'Avsättningar för pensioner enligt tryggandelagen', NULL, '1', '2210', 'Avsättningar för pensioner enligt tryggandelagen'),
(354, '222', 'Avsättningar för garantier', NULL, '1', '2220', 'Avsättningar för garantier'),
(355, '223', 'Övriga avsättningar för pensioner och liknande förpliktelser', NULL, NULL, '2230', 'Övriga avsättningar för pensioner och liknande förpliktelser'),
(356, '224', 'Avsättningar för uppskjutna skatter', 1, NULL, '2240', 'Avsättningar för uppskjutna skatter'),
(357, '225', 'Övriga avsättningar för skatter', NULL, NULL, '2250', 'Övriga avsättningar för skatter'),
(358, NULL, 'Övriga avsättningar för skatter', NULL, NULL, '2252', 'Avsättningar för tvistiga skatter'),
(359, NULL, 'Övriga avsättningar för skatter', NULL, NULL, '2253', 'Avsättningar särskild löneskatt, deklarationspost'),
(360, '229', 'Övriga avsättningar', NULL, '1', '2290', 'Övriga avsättningar'),
(361, '23', 'Långfristiga skulder', NULL, NULL, NULL, NULL),
(362, '231', 'Obligations- och förlagslån', NULL, NULL, '2310', 'Obligations- och förlagslån'),
(363, '232', 'Konvertibla lån och liknande', NULL, NULL, '2320', 'Konvertibla lån och liknande'),
(364, NULL, 'Konvertibla lån och liknande', NULL, NULL, '2321', 'Konvertibla lån'),
(365, NULL, 'Konvertibla lån och liknande', NULL, NULL, '2322', 'Lån förenade med optionsrätt'),
(366, NULL, 'Konvertibla lån och liknande', NULL, NULL, '2323', 'Vinstandelslån'),
(367, NULL, 'Konvertibla lån och liknande', NULL, NULL, '2324', 'Kapitalandelslån'),
(368, '233', 'Checkräkningskredit', NULL, '1', '2330', 'Checkräkningskredit'),
(369, NULL, 'Checkräkningskredit', NULL, NULL, '2331', 'Checkräkningskredit 1'),
(370, NULL, 'Checkräkningskredit', NULL, NULL, '2332', 'Checkräkningskredit 2'),
(371, '234', 'Byggnadskreditiv', NULL, NULL, '2340', 'Byggnadskreditiv'),
(372, '235', 'Andra långfristiga skulder till kreditinstitut', NULL, '1', '2350', 'Andra långfristiga skulder till kreditinstitut'),
(373, NULL, 'Andra långfristiga skulder till kreditinstitut', NULL, NULL, '2351', 'Fastighetslån, långfristig del'),
(374, NULL, 'Andra långfristiga skulder till kreditinstitut', NULL, NULL, '2355', 'Långfristiga lån i utländsk valuta från kreditinstitut'),
(375, NULL, 'Andra långfristiga skulder till kreditinstitut', NULL, NULL, '2359', 'Övriga långfristiga lån från kreditinstitut'),
(376, '236', 'Långfristiga skulder till koncernföretag', NULL, NULL, '2360', 'Långfristiga skulder till koncernföretag'),
(377, NULL, 'Långfristiga skulder till koncernföretag', NULL, NULL, '2361', 'Långfristiga skulder till moderföretag'),
(378, NULL, 'Långfristiga skulder till koncernföretag', NULL, NULL, '2362', 'Långfristiga skulder till dotterföretag'),
(379, NULL, 'Långfristiga skulder till koncernföretag', NULL, NULL, '2363', 'Långfristiga skulder till andra koncernföretag'),
(380, '237', 'Långfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '2370', 'Långfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(381, NULL, 'Långfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '2371', 'Långfristiga skulder till intresseföretag'),
(382, NULL, 'Långfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '2372', 'Långfristiga skulder till gemensamt styrda företag'),
(383, NULL, 'Långfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '2373', 'Långfristiga skulder till övriga företag som det finns ett ägarintresse i'),
(384, '239', 'Övriga långfristiga skulder', NULL, '1', '2390', 'Övriga långfristiga skulder'),
(385, NULL, 'Övriga långfristiga skulder', NULL, NULL, '2391', 'Avbetalningskontrakt, långfristig del'),
(386, NULL, 'Övriga långfristiga skulder', NULL, NULL, '2392', 'Villkorliga långfristiga skulder'),
(387, NULL, 'Övriga långfristiga skulder', NULL, '1', '2393', 'Lån från närstående personer, långfristig del'),
(388, NULL, 'Övriga långfristiga skulder', NULL, NULL, '2394', 'Långfristiga leverantörskrediter'),
(389, NULL, 'Övriga långfristiga skulder', NULL, NULL, '2395', 'Andra långfristiga lån i utländsk valuta'),
(390, NULL, 'Övriga långfristiga skulder', NULL, NULL, '2396', 'Derivat'),
(391, NULL, 'Övriga långfristiga skulder', NULL, NULL, '2397', 'Mottagna depositioner, långfristiga'),
(392, NULL, 'Övriga långfristiga skulder', NULL, NULL, '2399', 'Övriga långfristiga skulder'),
(393, '24', 'Kortfristiga skulder till kreditinstitut, kunder och leverantörer', NULL, NULL, NULL, NULL),
(394, '241', 'Andra kortfristiga låneskulder till kreditinstitut', NULL, '1', '2410', 'Andra kortfristiga låneskulder till kreditinstitut'),
(395, NULL, 'Andra kortfristiga låneskulder till kreditinstitut', NULL, NULL, '2411', 'Kortfristiga lån från kreditinstitut'),
(396, NULL, 'Andra kortfristiga låneskulder till kreditinstitut', NULL, NULL, '2412', 'Byggnadskreditiv, kortfristig del'),
(397, NULL, 'Andra kortfristiga låneskulder till kreditinstitut', NULL, NULL, '2417', 'Kortfristig del av långfristiga skulder till kreditinstitut'),
(398, NULL, 'Andra kortfristiga låneskulder till kreditinstitut', NULL, NULL, '2419', 'Övriga kortfristiga skulder till kreditinstitut'),
(399, '242', 'Förskott från kunder', NULL, '1', '2420', 'Förskott från kunder'),
(400, NULL, 'Förskott från kunder', NULL, NULL, '2421', 'Ej inlösta presentkort'),
(401, NULL, 'Förskott från kunder', NULL, NULL, '2429', 'Övriga förskott från kunder'),
(402, '243', 'Pågående arbeten', NULL, NULL, '2430', 'Pågående arbeten'),
(403, NULL, 'Pågående arbeten', NULL, NULL, '2431', 'Pågående arbeten, fakturering'),
(404, NULL, 'Pågående arbeten', NULL, NULL, '2438', 'Pågående arbeten, nedlagda kostnader'),
(405, NULL, 'Pågående arbeten', NULL, NULL, '2439', 'Beräknad förändring av pågående arbeten'),
(406, '244', 'Leverantörsskulder', NULL, '1', '2440', 'Leverantörsskulder'),
(407, NULL, 'Leverantörsskulder', NULL, NULL, '2441', 'Leverantörsskulder'),
(408, NULL, 'Leverantörsskulder', NULL, NULL, '2443', 'Konsignationsskulder'),
(409, NULL, 'Leverantörsskulder', NULL, NULL, '2445', 'Tvistiga leverantörsskulder'),
(410, NULL, 'Leverantörsskulder', 1, NULL, '2448', 'Ej reskontraförda leverantörsskulder'),
(411, '245', 'Fakturerad men ej upparbetad intäkt', NULL, NULL, '2450', 'Fakturerad men ej upparbetad intäkt'),
(412, '246', 'Leverantörsskulder till koncernföretag', NULL, NULL, '2460', 'Leverantörsskulder till koncernföretag'),
(413, NULL, 'Leverantörsskulder till koncernföretag', NULL, NULL, '2461', 'Leverantörsskulder till moderföretag'),
(414, NULL, 'Leverantörsskulder till koncernföretag', NULL, NULL, '2462', 'Leverantörsskulder till dotterföretag'),
(415, NULL, 'Leverantörsskulder till koncernföretag', NULL, NULL, '2463', 'Leverantörsskulder till andra koncernföretag'),
(416, '247', 'Leverantörsskulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '2470', 'Leverantörsskulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(417, NULL, 'Leverantörsskulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '2471', 'Leverantörsskulder till intresseföretag'),
(418, NULL, 'Leverantörsskulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '2472', 'Leverantörsskulder till gemensamt styrda företag'),
(419, NULL, 'Leverantörsskulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '2473', 'Leverantörsskulder till övriga företag som det finns ett ägarintresse i'),
(420, '248', 'Checkräkningskredit, kortfristig', NULL, '1', '2480', 'Checkräkningskredit, kortfristig'),
(421, '249', 'Övriga kortfristiga skulder till kreditinstitut, kunder och leverantörer', NULL, '1', '2490', 'Övriga kortfristiga skulder till kreditinstitut, kunder och leverantörer'),
(422, NULL, 'Övriga kortfristiga skulder till kreditinstitut, kunder och leverantörer', NULL, NULL, '2491', 'Avräkning spelarrangörer'),
(423, NULL, 'Övriga kortfristiga skulder till kreditinstitut, kunder och leverantörer', NULL, NULL, '2492', 'Växelskulder'),
(424, NULL, 'Övriga kortfristiga skulder till kreditinstitut, kunder och leverantörer', NULL, NULL, '2499', 'Andra övriga kortfristiga skulder'),
(425, '25', 'Skatteskulder', NULL, NULL, NULL, NULL),
(426, '251', 'Skatteskulder', NULL, '1', '2510', 'Skatteskulder'),
(427, NULL, 'Skatteskulder', NULL, NULL, '2512', 'Beräknad inkomstskatt'),
(428, NULL, 'Skatteskulder', NULL, NULL, '2513', 'Beräknad fastighetsskatt/fastighetsavgift'),
(429, NULL, 'Skatteskulder', NULL, NULL, '2514', 'Beräknad särskild löneskatt på pensionskostnader'),
(430, NULL, 'Skatteskulder', NULL, NULL, '2515', 'Beräknad avkastningsskatt'),
(431, NULL, 'Skatteskulder', NULL, NULL, '2517', 'Beräknad utländsk skatt'),
(432, NULL, 'Skatteskulder', NULL, NULL, '2518', 'Betald F-skatt'),
(433, '26', 'Moms och punktskatter', NULL, NULL, NULL, NULL),
(434, '261', 'Utgående moms, 25 %', NULL, '1', '2610', 'Utgående moms, 25 %'),
(435, NULL, 'Utgående moms, 25 %', NULL, '1', '2611', 'Utgående moms på försäljning inom Sverige, 25 %'),
(436, NULL, 'Utgående moms, 25 %', NULL, '1', '2612', 'Utgående moms på egna uttag, 25 %'),
(437, NULL, 'Utgående moms, 25 %', NULL, '1', '2613', 'Utgående moms för uthyrning, 25 %'),
(438, NULL, 'Utgående moms, 25 %', NULL, '1', '2614', 'Utgående moms, omvänd betalningsskyldighet, 25 %'),
(439, NULL, 'Utgående moms, 25 %', NULL, '1', '2615', 'Utgående moms import av varor, 25 %'),
(440, NULL, 'Utgående moms, 25 %', NULL, '1', '2616', 'Utgående moms VMB 25 %'),
(441, NULL, 'Utgående moms, 25 %', NULL, NULL, '2618', 'Vilande utgående moms, 25 %'),
(442, '262', 'Utgående moms, 12 %', NULL, '1', '2620', 'Utgående moms, 12 %'),
(443, NULL, 'Utgående moms, 12 %', NULL, '1', '2621', 'Utgående moms på försäljning inom Sverige, 12 %'),
(444, NULL, 'Utgående moms, 12 %', NULL, '1', '2622', 'Utgående moms på egna uttag, 12 %'),
(445, NULL, 'Utgående moms, 12 %', NULL, '1', '2623', 'Utgående moms för uthyrning, 12 %'),
(446, NULL, 'Utgående moms, 12 %', NULL, '1', '2624', 'Utgående moms, omvänd betalningsskyldighet, 12 %'),
(447, NULL, 'Utgående moms, 12 %', NULL, '1', '2625', 'Utgående moms import av varor, 12 %'),
(448, NULL, 'Utgående moms, 12 %', NULL, '1', '2626', 'Utgående moms VMB 12 %'),
(449, NULL, 'Utgående moms, 12 %', NULL, NULL, '2628', 'Vilande utgående moms, 12 %'),
(450, '263', 'Utgående moms, 6 %', NULL, '1', '2630', 'Utgående moms, 6 %'),
(451, NULL, 'Utgående moms, 6 %', NULL, '1', '2631', 'Utgående moms på försäljning inom Sverige, 6 %'),
(452, NULL, 'Utgående moms, 6 %', NULL, '1', '2632', 'Utgående moms på egna uttag, 6 %'),
(453, NULL, 'Utgående moms, 6 %', NULL, '1', '2633', 'Utgående moms för uthyrning, 6 %'),
(454, NULL, 'Utgående moms, 6 %', NULL, '1', '2634', 'Utgående moms, omvänd betalningsskyldighet, 6 %'),
(455, NULL, 'Utgående moms, 6 %', NULL, '1', '2635', 'Utgående moms import av varor, 6 %'),
(456, NULL, 'Utgående moms, 6 %', NULL, '1', '2636', 'Utgående moms VMB 6 %'),
(457, NULL, 'Utgående moms, 6 %', NULL, NULL, '2638', 'Vilande utgående moms, 6 %'),
(458, '264', 'Ingående moms', NULL, '1', '2640', 'Ingående moms'),
(459, NULL, 'Ingående moms', NULL, '1', '2641', 'Debiterad ingående moms'),
(460, NULL, 'Ingående moms', NULL, '1', '2642', 'Debiterad ingående moms i anslutning till frivillig betalningsskyldighet'),
(461, NULL, 'Ingående moms', NULL, '1', '2645', 'Beräknad ingående moms på förvärv från utlandet'),
(462, NULL, 'Ingående moms', NULL, '1', '2646', 'Ingående moms på uthyrning'),
(463, NULL, 'Ingående moms', NULL, '1', '2647', 'Ingående moms, omvänd betalningsskyldighet varor och tjänster i Sverige'),
(464, NULL, 'Ingående moms', NULL, '1', '2648', 'Vilande ingående moms'),
(465, NULL, 'Ingående moms', NULL, '1', '2649', 'Ingående moms, blandad verksamhet'),
(466, '265', 'Redovisningskonto för moms', NULL, '1', '2650', 'Redovisningskonto för moms'),
(467, '266', 'Punktskatter', NULL, NULL, '2660', 'Punktskatter'),
(468, '267', 'Utgående moms, OSS', NULL, NULL, '2670', 'Utgående moms på försäljning inom EU, OSS'),
(469, '27', 'Personalens skatter, avgifter och löneavdrag', NULL, NULL, NULL, NULL),
(470, '271', 'Personalskatt', NULL, '1', '2710', 'Personalskatt'),
(471, '273', 'Lagstadgade sociala avgifter och särskild löneskatt', NULL, '1', '2730', 'Lagstadgade sociala avgifter och särskild löneskatt'),
(472, NULL, 'Lagstadgade sociala avgifter och särskild löneskatt', NULL, NULL, '2731', 'Avräkning lagstadgade sociala avgifter'),
(473, NULL, 'Lagstadgade sociala avgifter och särskild löneskatt', NULL, NULL, '2732', 'Avräkning särskild löneskatt'),
(474, '274', 'Avtalade sociala avgifter', NULL, '1', '2740', 'Avtalade sociala avgifter'),
(475, '275', 'Utmätning i lön m.m.', NULL, NULL, '2750', 'Utmätning i lön m.m.'),
(476, '276', 'Semestermedel', NULL, NULL, '2760', 'Semestermedel'),
(477, NULL, 'Semestermedel', NULL, NULL, '2761', 'Avräkning semesterlöner'),
(478, NULL, 'Semestermedel', NULL, NULL, '2762', 'Semesterlönekassa'),
(479, '279', 'Övriga löneavdrag', NULL, '1', '2790', 'Övriga löneavdrag'),
(480, NULL, 'Övriga löneavdrag', NULL, NULL, '2791', 'Personalens intressekonto'),
(481, NULL, 'Övriga löneavdrag', NULL, NULL, '2792', 'Lönsparande'),
(482, NULL, 'Övriga löneavdrag', NULL, NULL, '2793', 'Gruppförsäkringspremier'),
(483, NULL, 'Övriga löneavdrag', NULL, NULL, '2794', 'Fackföreningsavgifter'),
(484, NULL, 'Övriga löneavdrag', NULL, NULL, '2795', 'Mätnings- och granskningsarvoden'),
(485, NULL, 'Övriga löneavdrag', NULL, NULL, '2799', 'Övriga löneavdrag');
INSERT INTO `chart_of_accounts` (`id`, `main_account`, `main_account_description`, `no_k2`, `simple_account`, `sub_account`, `sub_account_description`) VALUES
(486, '28', 'Övriga kortfristiga skulder', NULL, NULL, NULL, NULL),
(487, '281', 'Avräkning för factoring och belånade kontraktsfordringar', NULL, NULL, '2810', 'Avräkning för factoring och belånade kontraktsfordringar'),
(488, NULL, 'Avräkning för factoring och belånade kontraktsfordringar', NULL, NULL, '2811', 'Avräkning för factoring'),
(489, NULL, 'Avräkning för factoring och belånade kontraktsfordringar', NULL, NULL, '2812', 'Avräkning för belånade kontraktsfordringar'),
(490, '282', 'Kortfristiga skulder till anställda', NULL, '1', '2820', 'Kortfristiga skulder till anställda'),
(491, NULL, 'Kortfristiga skulder till anställda', NULL, NULL, '2821', 'Löneskulder'),
(492, NULL, 'Kortfristiga skulder till anställda', NULL, NULL, '2822', 'Reseräkningar'),
(493, NULL, 'Kortfristiga skulder till anställda', NULL, NULL, '2823', 'Tantiem, gratifikationer'),
(494, NULL, 'Kortfristiga skulder till anställda', NULL, NULL, '2829', 'Övriga kortfristiga skulder till anställda'),
(495, '283', 'Avräkning för annans räkning', NULL, NULL, '2830', 'Avräkning för annans räkning'),
(496, '284', 'Kortfristiga låneskulder', NULL, '1', '2840', 'Kortfristiga låneskulder'),
(497, NULL, 'Kortfristiga låneskulder', NULL, NULL, '2841', 'Kortfristig del av långfristiga skulder'),
(498, NULL, 'Kortfristiga låneskulder', NULL, NULL, '2849', 'Övriga kortfristiga låneskulder'),
(499, '285', 'Avräkning för skatter och avgifter (skattekonto)', NULL, NULL, '2850', 'Avräkning för skatter och avgifter (skattekonto)'),
(500, NULL, 'Avräkning för skatter och avgifter (skattekonto)', NULL, NULL, '2852', 'Anståndsbelopp för moms, arbetsgivaravgifter och personalskatt'),
(501, '286', 'Kortfristiga skulder till koncernföretag', NULL, NULL, '2860', 'Kortfristiga skulder till koncernföretag'),
(502, NULL, 'Kortfristiga skulder till koncernföretag', NULL, NULL, '2861', 'Kortfristiga skulder till moderföretag'),
(503, NULL, 'Kortfristiga skulder till koncernföretag', NULL, NULL, '2862', 'Kortfristiga skulder till dotterföretag'),
(504, NULL, 'Kortfristiga skulder till koncernföretag', NULL, NULL, '2863', 'Kortfristiga skulder till andra koncernföretag'),
(505, '287', 'Kortfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '2870', 'Kortfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(506, NULL, 'Kortfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '2871', 'Kortfristiga skulder till intresseföretag'),
(507, NULL, 'Kortfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '2872', 'Kortfristiga skulder till gemensamt styrda företag'),
(508, NULL, 'Kortfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '2873', 'Kortfristiga skulder till övriga företag som det finns ett ägarintresse i'),
(509, '288', 'Skuld erhållna bidrag', NULL, NULL, '2880', 'Skuld erhållna bidrag'),
(510, '289', 'Övriga kortfristiga skulder', NULL, '1', '2890', 'Övriga kortfristiga skulder'),
(511, NULL, 'Övriga kortfristiga skulder', NULL, NULL, '2891', 'Skulder under indrivning'),
(512, NULL, 'Övriga kortfristiga skulder', NULL, NULL, '2892', 'Inre reparationsfond/underhållsfond'),
(513, NULL, 'Övriga kortfristiga skulder', NULL, NULL, '2893', 'Skulder till närstående personer, kortfristig del'),
(514, NULL, 'Övriga kortfristiga skulder', NULL, NULL, '2895', 'Derivat (kortfristiga skulder)'),
(515, NULL, 'Övriga kortfristiga skulder', NULL, NULL, '2897', 'Mottagna depositioner, kortfristiga'),
(516, NULL, 'Övriga kortfristiga skulder', NULL, NULL, '2898', 'Outtagen vinstutdelning'),
(517, NULL, 'Övriga kortfristiga skulder', NULL, NULL, '2899', 'Övriga kortfristiga skulder'),
(518, '29', 'Upplupna kostnader och förutbetalda intäkter', NULL, NULL, NULL, NULL),
(519, '291', 'Upplupna löner', NULL, '1', '2910', 'Upplupna löner'),
(520, NULL, 'Upplupna löner', NULL, NULL, '2911', 'Löneskulder'),
(521, NULL, 'Upplupna löner', NULL, NULL, '2912', 'Ackordsöverskott'),
(522, NULL, 'Upplupna löner', NULL, NULL, '2919', 'Övriga upplupna löner'),
(523, '292', 'Upplupna semesterlöner', NULL, '1', '2920', 'Upplupna semesterlöner'),
(524, '293', 'Upplupna pensionskostnader', NULL, NULL, '2930', 'Upplupna pensionskostnader'),
(525, NULL, 'Upplupna pensionskostnader', NULL, NULL, '2931', 'Upplupna pensionsutbetalningar'),
(526, '294', 'Upplupna lagstadgade sociala och andra avgifter', NULL, '1', '2940', 'Upplupna lagstadgade sociala och andra avgifter'),
(527, NULL, 'Upplupna lagstadgade sociala och andra avgifter', NULL, NULL, '2941', 'Beräknade upplupna lagstadgade sociala avgifter'),
(528, NULL, 'Upplupna lagstadgade sociala och andra avgifter', NULL, NULL, '2942', 'Beräknad upplupen särskild löneskatt'),
(529, NULL, 'Upplupna lagstadgade sociala och andra avgifter', NULL, NULL, '2943', 'Beräknad upplupen särskild löneskatt på pensionskostnader, deklarationspost'),
(530, NULL, 'Upplupna lagstadgade sociala och andra avgifter', NULL, NULL, '2944', 'Beräknad upplupen avkastningsskatt på pensionskostnader'),
(531, '295', 'Upplupna avtalade sociala avgifter', NULL, '1', '2950', 'Upplupna avtalade sociala avgifter'),
(532, NULL, 'Upplupna avtalade sociala avgifter', NULL, NULL, '2951', 'Upplupna avtalade arbetsmarknadsförsäkringar'),
(533, NULL, 'Upplupna avtalade sociala avgifter', NULL, NULL, '2959', 'Upplupna avtalade pensionsförsäkringsavgifter, deklarationspost'),
(534, '296', 'Upplupna räntekostnader', NULL, '1', '2960', 'Upplupna räntekostnader'),
(535, '297', 'Förutbetalda intäkter', NULL, '1', '2970', 'Förutbetalda intäkter'),
(536, NULL, 'Förutbetalda intäkter', NULL, NULL, '2971', 'Förutbetalda hyresintäkter'),
(537, NULL, 'Förutbetalda intäkter', NULL, NULL, '2972', 'Förutbetalda medlemsavgifter'),
(538, NULL, 'Förutbetalda intäkter', NULL, NULL, '2979', 'Övriga förutbetalda intäkter'),
(539, '298', 'Upplupna avtalskostnader', NULL, NULL, '2980', 'Upplupna avtalskostnader'),
(540, '299', 'Övriga upplupna kostnader och förutbetalda intäkter', NULL, '1', '2990', 'Övriga upplupna kostnader och förutbetalda intäkter'),
(541, NULL, 'Övriga upplupna kostnader och förutbetalda intäkter', NULL, NULL, '2991', 'Beräknat arvode för bokslut'),
(542, NULL, 'Övriga upplupna kostnader och förutbetalda intäkter', NULL, NULL, '2992', 'Beräknat arvode för revision'),
(543, NULL, 'Övriga upplupna kostnader och förutbetalda intäkter', NULL, NULL, '2993', 'Ospecificerad skuld till leverantörer'),
(544, NULL, 'Övriga upplupna kostnader och förutbetalda intäkter', NULL, '1', '2995', 'Ej ankomna leverantörsfakturor'),
(545, NULL, 'Övriga upplupna kostnader och förutbetalda intäkter', NULL, NULL, '2998', 'Övriga upplupna kostnader och förutbetalda intäkter'),
(546, NULL, 'Övriga upplupna kostnader och förutbetalda intäkter', NULL, '1', '2999', 'OBS-konto'),
(547, '3', 'Rörelsens inkomster/intäkter', NULL, NULL, NULL, NULL),
(548, '30', 'Huvudintäkter', NULL, NULL, NULL, NULL),
(549, '300', 'Försäljning inom Sverige', NULL, '1', '3000', 'Försäljning inom Sverige'),
(550, NULL, 'Försäljning inom Sverige', NULL, '1', '3001', 'Försäljning inom Sverige, 25 % moms'),
(551, NULL, 'Försäljning inom Sverige', NULL, '1', '3002', 'Försäljning inom Sverige, 12 % moms'),
(552, NULL, 'Försäljning inom Sverige', NULL, '1', '3003', 'Försäljning inom Sverige, 6 % moms'),
(553, NULL, 'Försäljning inom Sverige', NULL, '1', '3004', 'Försäljning inom Sverige, momsfri'),
(554, '31', 'Huvudintäkter', NULL, NULL, NULL, NULL),
(555, '310', 'Försäljning av varor utanför Sverige', NULL, '1', '3100', 'Försäljning av varor utanför Sverige'),
(556, NULL, 'Försäljning av varor utanför Sverige', NULL, '1', '3105', 'Försäljning varor till land utanför EU'),
(557, NULL, 'Försäljning av varor utanför Sverige', NULL, '1', '3106', 'Försäljning varor till annat EU-land, momspliktig'),
(558, NULL, 'Försäljning av varor utanför Sverige', NULL, '1', '3108', 'Försäljning varor till annat EU-land, momsfri'),
(559, '32', 'Huvudintäkter', NULL, NULL, NULL, NULL),
(560, '320', 'Försäljning VMB och omvänd moms', NULL, '1', '3200', 'Försäljning VMB och omvänd moms'),
(561, '321', 'Försäljning positiv VMB 25 %', NULL, '1', '3211', 'Försäljning positiv VMB 25 %'),
(562, NULL, 'Försäljning positiv VMB 25 %', NULL, '1', '3212', 'Försäljning negativ VMB 25 %'),
(563, '323', 'Försäljning inom byggsektorn, omvänd betalningsskyldighet moms', NULL, '1', '3231', 'Försäljning inom byggsektorn, omvänd betalningsskyldighet moms'),
(564, '33', 'Huvudintäkter', NULL, NULL, NULL, NULL),
(565, '330', 'Försäljning av tjänster utanför Sverige', NULL, '1', '3300', 'Försäljning av tjänster utanför Sverige'),
(566, NULL, 'Försäljning av tjänster utanför Sverige', NULL, '1', '3305', 'Försäljning tjänster till land utanför EU'),
(567, NULL, 'Försäljning av tjänster utanför Sverige', NULL, '1', '3308', 'Försäljning tjänster till annat EU-land'),
(568, '34', 'Huvudintäkter', NULL, NULL, NULL, NULL),
(569, '340', 'Försäljning, egna uttag', NULL, '1', '3400', 'Försäljning, egna uttag'),
(570, NULL, 'Försäljning, egna uttag', NULL, '1', '3401', 'Egna uttag momspliktiga, 25 %'),
(571, NULL, 'Försäljning, egna uttag', NULL, '1', '3402', 'Egna uttag momspliktiga, 12 %'),
(572, NULL, 'Försäljning, egna uttag', NULL, '1', '3403', 'Egna uttag momspliktiga, 6 %'),
(573, NULL, 'Försäljning, egna uttag', NULL, '1', '3404', 'Egna uttag, momsfria'),
(574, '35', 'Fakturerade kostnader', NULL, NULL, NULL, NULL),
(575, '350', 'Fakturerade kostnader (gruppkonto)', NULL, '1', '3500', 'Fakturerade kostnader (gruppkonto)'),
(576, '351', 'Fakturerat emballage', NULL, '1', '3510', 'Fakturerat emballage'),
(577, NULL, 'Fakturerat emballage', NULL, NULL, '3511', 'Fakturerat emballage'),
(578, NULL, 'Fakturerat emballage', NULL, NULL, '3518', 'Returnerat emballage'),
(579, '352', 'Fakturerade frakter', NULL, '1', '3520', 'Fakturerade frakter'),
(580, NULL, 'Fakturerade frakter', NULL, '1', '3521', 'Fakturerade frakter, EU-land'),
(581, NULL, 'Fakturerade frakter', NULL, '1', '3522', 'Fakturerade frakter, export'),
(582, '353', 'Fakturerade tull- och speditionskostnader m.m.', NULL, '1', '3530', 'Fakturerade tull- och speditionskostnader m.m.'),
(583, '354', 'Faktureringsavgifter', NULL, '1', '3540', 'Faktureringsavgifter'),
(584, NULL, 'Faktureringsavgifter', NULL, '1', '3541', 'Faktureringsavgifter, EU-land'),
(585, NULL, 'Faktureringsavgifter', NULL, '1', '3542', 'Faktureringsavgifter, export'),
(586, '355', 'Fakturerade resekostnader', NULL, NULL, '3550', 'Fakturerade resekostnader'),
(587, '356', 'Fakturerade kostnader till koncernföretag', NULL, NULL, '3560', 'Fakturerade kostnader till koncernföretag'),
(588, NULL, 'Fakturerade kostnader till koncernföretag', NULL, NULL, '3561', 'Fakturerade kostnader till moderföretag'),
(589, NULL, 'Fakturerade kostnader till koncernföretag', NULL, NULL, '3562', 'Fakturerade kostnader till dotterföretag'),
(590, NULL, 'Fakturerade kostnader till koncernföretag', NULL, NULL, '3563', 'Fakturerade kostnader till andra koncernföretag'),
(591, '357', 'Fakturerade kostnader till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '3570', 'Fakturerade kostnader till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(592, '359', 'Övriga fakturerade kostnader', NULL, NULL, '3590', 'Övriga fakturerade kostnader'),
(593, '36', 'Rörelsens sidointäkter', NULL, NULL, NULL, NULL),
(594, '360', 'Rörelsens sidointäkter (gruppkonto)', NULL, '1', '3600', 'Rörelsens sidointäkter (gruppkonto)'),
(595, '361', 'Försäljning av material', NULL, NULL, '3610', 'Försäljning av material'),
(596, NULL, 'Försäljning av material', NULL, NULL, '3611', 'Försäljning av råmaterial'),
(597, NULL, 'Försäljning av material', NULL, NULL, '3612', 'Försäljning av skrot'),
(598, NULL, 'Försäljning av material', NULL, NULL, '3613', 'Försäljning av förbrukningsmaterial'),
(599, NULL, 'Försäljning av material', NULL, NULL, '3619', 'Försäljning av övrigt material'),
(600, '362', 'Tillfällig uthyrning av personal', NULL, NULL, '3620', 'Tillfällig uthyrning av personal'),
(601, '363', 'Tillfällig uthyrning av transportmedel', NULL, NULL, '3630', 'Tillfällig uthyrning av transportmedel'),
(602, '367', 'Intäkter från värdepapper', NULL, NULL, '3670', 'Intäkter från värdepapper'),
(603, NULL, 'Intäkter från värdepapper', NULL, NULL, '3671', 'Försäljning av värdepapper'),
(604, NULL, 'Intäkter från värdepapper', NULL, NULL, '3672', 'Utdelning från värdepapper'),
(605, NULL, 'Intäkter från värdepapper', NULL, NULL, '3679', 'Övriga intäkter från värdepapper'),
(606, '368', 'Management fees', NULL, NULL, '3680', 'Management fees'),
(607, '369', 'Övriga sidointäkter', NULL, NULL, '3690', 'Övriga sidointäkter'),
(608, '37', 'Intäktskorrigeringar', NULL, NULL, NULL, NULL),
(609, '370', 'Intäktskorrigeringar (gruppkonto)', NULL, NULL, '3700', 'Intäktskorrigeringar (gruppkonto)'),
(610, '371', 'Ofördelade intäktsreduktioner', NULL, NULL, '3710', 'Ofördelade intäktsreduktioner'),
(611, '373', 'Lämnade rabatter', NULL, '1', '3730', 'Lämnade rabatter'),
(612, NULL, 'Lämnade rabatter', NULL, NULL, '3731', 'Lämnade kassarabatter'),
(613, NULL, 'Lämnade rabatter', NULL, NULL, '3732', 'Lämnade mängdrabatter'),
(614, '374', 'Öres- och kronutjämning', NULL, '1', '3740', 'Öres- och kronutjämning'),
(615, '375', 'Punktskatter', NULL, NULL, '3750', 'Punktskatter'),
(616, NULL, 'Punktskatter', NULL, NULL, '3751', 'Intäktsförda punktskatter (kreditkonto)'),
(617, NULL, 'Punktskatter', NULL, NULL, '3752', 'Skuldförda punktskatter (debetkonto)'),
(618, '379', 'Övriga intäktskorrigeringar', NULL, NULL, '3790', 'Övriga intäktskorrigeringar'),
(619, '38', 'Aktiverat arbete för egen räkning', NULL, NULL, NULL, NULL),
(620, '380', 'Aktiverat arbete för egen räkning (gruppkonto)', NULL, '1', '3800', 'Aktiverat arbete för egen räkning (gruppkonto)'),
(621, '384', 'Aktiverat arbete (material)', NULL, NULL, '3840', 'Aktiverat arbete (material)'),
(622, '385', 'Aktiverat arbete (omkostnader)', NULL, NULL, '3850', 'Aktiverat arbete (omkostnader)'),
(623, '387', 'Aktiverat arbete (personal)', NULL, NULL, '3870', 'Aktiverat arbete (personal)'),
(624, '39', 'Övriga rörelseintäkter', NULL, NULL, NULL, NULL),
(625, '390', 'Övriga rörelseintäkter (gruppkonto)', NULL, '1', '3900', 'Övriga rörelseintäkter (gruppkonto)'),
(626, '391', 'Hyres- och arrendeintäkter', NULL, NULL, '3910', 'Hyres- och arrendeintäkter'),
(627, NULL, 'Hyres- och arrendeintäkter', NULL, NULL, '3911', 'Hyresintäkter'),
(628, NULL, 'Hyres- och arrendeintäkter', NULL, NULL, '3912', 'Arrendeintäkter'),
(629, NULL, 'Hyres- och arrendeintäkter', NULL, '1', '3913', 'Frivilligt momspliktiga hyresintäkter'),
(630, NULL, 'Hyres- och arrendeintäkter', NULL, NULL, '3914', 'Övriga momspliktiga hyresintäkter'),
(631, '392', 'Provisionsintäkter, licensintäkter och royalties', NULL, NULL, '3920', 'Provisionsintäkter, licensintäkter och royalties'),
(632, NULL, 'Provisionsintäkter, licensintäkter och royalties', NULL, NULL, '3921', 'Provisionsintäkter'),
(633, NULL, 'Provisionsintäkter, licensintäkter och royalties', NULL, NULL, '3922', 'Licensintäkter och royalties'),
(634, NULL, 'Provisionsintäkter, licensintäkter och royalties', NULL, NULL, '3925', 'Franchiseintäkter'),
(635, '394', 'Orealiserade negativa/positiva värdeförändringar på säkringsinstrument', 1, NULL, '3940', 'Orealiserade negativa/positiva värdeförändringar på säkringsinstrument'),
(636, '395', 'Återvunna, tidigare avskrivna kundfordringar', NULL, NULL, '3950', 'Återvunna, tidigare avskrivna kundfordringar'),
(637, '396', 'Valutakursvinster på fordringar och skulder av rörelsekaraktär', NULL, '1', '3960', 'Valutakursvinster på fordringar och skulder av rörelsekaraktär'),
(638, '397', 'Vinst vid avyttring av immateriella och materiella anläggningstillgångar', NULL, '1', '3970', 'Vinst vid avyttring av immateriella och materiella anläggningstillgångar'),
(639, NULL, 'Vinst vid avyttring av immateriella och materiella anläggningstillgångar', NULL, NULL, '3971', 'Vinst vid avyttring av immateriella anläggningstillgångar'),
(640, NULL, 'Vinst vid avyttring av immateriella och materiella anläggningstillgångar', NULL, NULL, '3972', 'Vinst vid avyttring av byggnader och mark'),
(641, NULL, 'Vinst vid avyttring av immateriella och materiella anläggningstillgångar', NULL, NULL, '3973', 'Vinst vid avyttring av maskiner och inventarier'),
(642, '398', 'Erhållna offentliga bidrag', NULL, '1', '3980', 'Erhållna offentliga bidrag'),
(643, NULL, 'Erhållna offentliga bidrag', NULL, NULL, '3981', 'Erhållna EU-bidrag'),
(644, NULL, 'Erhållna offentliga bidrag', NULL, NULL, '3985', 'Erhållna statliga bidrag'),
(645, NULL, 'Erhållna offentliga bidrag', NULL, NULL, '3987', 'Erhållna kommunala bidrag'),
(646, NULL, 'Erhållna offentliga bidrag', NULL, NULL, '3988', 'Erhållna offentliga bidrag för personal'),
(647, NULL, 'Erhållna offentliga bidrag', NULL, NULL, '3989', 'Övriga erhållna offentliga bidrag'),
(648, '399', 'Övriga ersättningar, bidrag och intäkter', NULL, NULL, '3990', 'Övriga ersättningar, bidrag och intäkter'),
(649, NULL, 'Övriga ersättningar, bidrag och intäkter', NULL, NULL, '3991', 'Konfliktersättning'),
(650, NULL, 'Övriga ersättningar, bidrag och intäkter', NULL, NULL, '3992', 'Erhållna skadestånd'),
(651, NULL, 'Övriga ersättningar, bidrag och intäkter', NULL, NULL, '3993', 'Erhållna donationer och gåvor'),
(652, NULL, 'Övriga ersättningar, bidrag och intäkter', NULL, NULL, '3994', 'Försäkringsersättningar'),
(653, NULL, 'Övriga ersättningar, bidrag och intäkter', NULL, NULL, '3995', 'Erhållet ackord på skulder av rörelsekaraktär'),
(654, NULL, 'Övriga ersättningar, bidrag och intäkter', NULL, NULL, '3996', 'Erhållna reklambidrag'),
(655, NULL, 'Övriga ersättningar, bidrag och intäkter', NULL, NULL, '3997', 'Sjuklöneersättning'),
(656, NULL, 'Övriga ersättningar, bidrag och intäkter', NULL, NULL, '3998', 'Återbäring av överskott från försäkringsföretag'),
(657, NULL, 'Övriga ersättningar, bidrag och intäkter', NULL, NULL, '3999', 'Övriga rörelseintäkter'),
(658, '4', 'Utgifter/kostnader för varor, material och vissa köpta tjänster', NULL, NULL, NULL, NULL),
(659, '40', 'Inköp av varor och material', NULL, NULL, NULL, NULL),
(660, '400', 'Inköp av varor från Sverige', NULL, '1', '4000', 'Inköp av varor från Sverige'),
(661, '41', 'Inköp av varor och material', NULL, NULL, NULL, NULL),
(662, '42', 'Inköp av varor och material', NULL, NULL, NULL, NULL),
(663, '420', 'Sålda varor VMB', NULL, '1', '4200', 'Sålda varor VMB'),
(664, '421', 'Sålda varor VMB 25 %', NULL, '1', '4211', 'Sålda varor positiv VMB 25 %'),
(665, NULL, NULL, NULL, '1', '4212', 'Sålda varor negativ VMB 25 %'),
(666, '43', 'Inköp av varor och material', NULL, NULL, NULL, NULL),
(667, '44', 'Inköp av varor och material', NULL, NULL, NULL, NULL),
(668, '440', 'Momspliktiga inköp i Sverige', NULL, '1', '4400', 'Momspliktiga inköp i Sverige'),
(669, '441', 'Inköpta varor i Sverige, omvänd betalningsskyldighet', NULL, '1', '4415', 'Inköpta varor i Sverige, omvänd betalningsskyldighet, 25 % moms'),
(670, NULL, 'Inköpta varor i Sverige, omvänd betalningsskyldighet', NULL, NULL, '4416', 'Inköpta varor i Sverige, omvänd betalningsskyldighet, 12 % moms'),
(671, NULL, 'Inköpta varor i Sverige, omvänd betalningsskyldighet', NULL, NULL, '4417', 'Inköpta varor i Sverige, omvänd betalningsskyldighet, 6 % moms'),
(672, '442', 'Inköpta tjänster i Sverige, omvänd betalningsskyldighet', NULL, NULL, '4425', 'Inköpta tjänster i Sverige, omvänd betalningsskyldighet, 25 % moms'),
(673, NULL, 'Inköpta tjänster i Sverige, omvänd betalningsskyldighet', NULL, '1', '4426', 'Inköpta tjänster i Sverige, omvänd betalningsskyldighet, 12 % moms'),
(674, NULL, 'Inköpta tjänster i Sverige, omvänd betalningsskyldighet', NULL, '1', '4427', 'Inköpta tjänster i Sverige, omvänd betalningsskyldighet, 6 % moms'),
(675, '45', 'Inköp av varor och material', NULL, NULL, NULL, NULL),
(676, '450', 'Övriga momspliktiga inköp', NULL, '1', '4500', 'Övriga momspliktiga inköp'),
(677, '451', 'Inköp av varor från annat EU-land', NULL, '1', '4515', 'Inköp av varor från annat EU-land, 25 %'),
(678, NULL, 'Inköp av varor från annat EU-land', NULL, '1', '4516', 'Inköp av varor från annat EU-land, 12 %'),
(679, NULL, 'Inköp av varor från annat EU-land', NULL, '1', '4517', 'Inköp av varor från annat EU-land, 6 %'),
(680, NULL, 'Inköp av varor från annat EU-land', NULL, '1', '4518', 'Inköp av varor från annat EU-land, momsfri'),
(681, '453', 'Inköp av tjänster från ett land utanför EU', NULL, '1', '4531', 'Inköp av tjänster från ett land utanför EU, 25 % moms'),
(682, NULL, 'Inköp av tjänster från ett land utanför EU', NULL, '1', '4532', 'Inköp av tjänster från ett land utanför EU, 12 % moms'),
(683, NULL, 'Inköp av tjänster från ett land utanför EU', NULL, '1', '4533', 'Inköp av tjänster från ett land utanför EU, 6 % moms'),
(684, NULL, 'Inköp av tjänster från ett land utanför EU', NULL, '1', '4535', 'Inköp av tjänster från annat EU-land, 25 %'),
(685, NULL, 'Inköp av tjänster från ett land utanför EU', NULL, '1', '4536', 'Inköp av tjänster från annat EU-land, 12 %'),
(686, NULL, 'Inköp av tjänster från ett land utanför EU', NULL, '1', '4537', 'Inköp av tjänster från annat EU-land, 6 %'),
(687, NULL, 'Inköp av tjänster från ett land utanför EU', NULL, '1', '4538', 'Inköp av tjänster från annat EU-land, momsfri'),
(688, '454', 'Import av varor', NULL, '1', '4545', 'Import av varor, 25 % moms'),
(689, NULL, 'Import av varor', NULL, '1', '4546', 'Import av varor, 12 % moms'),
(690, NULL, 'Import av varor', NULL, '1', '4547', 'Import av varor, 6 % moms'),
(691, '46', 'Legoarbeten, underentreprenader', NULL, NULL, NULL, NULL),
(692, '460', 'Legoarbeten och underentreprenader (gruppkonto)', NULL, '1', '4600', 'Legoarbeten och underentreprenader (gruppkonto)'),
(693, '47', 'Reduktion av inköpspriser', NULL, NULL, NULL, NULL),
(694, '470', 'Reduktion av inköpspriser (gruppkonto)', NULL, '1', '4700', 'Reduktion av inköpspriser (gruppkonto)'),
(695, '473', 'Erhållna rabatter', NULL, NULL, '4730', 'Erhållna rabatter'),
(696, NULL, 'Erhållna rabatter', NULL, NULL, '4731', 'Erhållna kassarabatter'),
(697, NULL, 'Erhållna rabatter', NULL, NULL, '4732', 'Erhållna mängdrabatter (inkl. bonus)'),
(698, NULL, 'Erhållna rabatter', NULL, NULL, '4733', 'Erhållet aktivitetsstöd'),
(699, '479', 'Övriga reduktioner av inköpspriser', NULL, NULL, '4790', 'Övriga reduktioner av inköpspriser'),
(700, '48', '(Fri kontogrupp)', NULL, NULL, NULL, NULL),
(701, '49', 'Förändring av lager, produkter i arbete och pågående arbeten', NULL, NULL, NULL, NULL),
(702, '490', 'Förändring av lager (gruppkonto)', NULL, '1', '4900', 'Förändring av lager (gruppkonto)'),
(703, '491', 'Förändring av lager av råvaror', NULL, '1', '4910', 'Förändring av lager av råvaror'),
(704, '492', 'Förändring av lager av tillsatsmaterial och förnödenheter', NULL, '1', '4920', 'Förändring av lager av tillsatsmaterial och förnödenheter'),
(705, '494', 'Förändring av produkter i arbete', NULL, '1', '4940', 'Förändring av produkter i arbete'),
(706, NULL, 'Förändring av produkter i arbete', NULL, NULL, '4944', 'Förändring av produkter i arbete, material och utlägg'),
(707, NULL, 'Förändring av produkter i arbete', NULL, NULL, '4945', 'Förändring av produkter i arbete, omkostnader'),
(708, NULL, 'Förändring av produkter i arbete', NULL, NULL, '4947', 'Förändring av produkter i arbete, personalkostnader'),
(709, '495', 'Förändring av lager av färdiga varor', NULL, '1', '4950', 'Förändring av lager av färdiga varor'),
(710, '496', 'Förändring av lager av handelsvaror', NULL, '1', '4960', 'Förändring av lager av handelsvaror'),
(711, '497', 'Förändring av pågående arbeten, nedlagda kostnader', NULL, '1', '4970', 'Förändring av pågående arbeten, nedlagda kostnader'),
(712, NULL, 'Förändring av pågående arbeten, nedlagda kostnader', NULL, NULL, '4974', 'Förändring av pågående arbeten, material och utlägg'),
(713, NULL, 'Förändring av pågående arbeten, nedlagda kostnader', NULL, NULL, '4975', 'Förändring av pågående arbeten, omkostnader'),
(714, NULL, 'Förändring av pågående arbeten, nedlagda kostnader', NULL, NULL, '4977', 'Förändring av pågående arbeten, personalkostnader'),
(715, '498', 'Förändring av lager av värdepapper', NULL, NULL, '4980', 'Förändring av lager av värdepapper'),
(716, NULL, 'Förändring av lager av värdepapper', NULL, NULL, '4981', 'Sålda värdepappers anskaffningsvärde'),
(717, NULL, 'Förändring av lager av värdepapper', NULL, NULL, '4987', 'Nedskrivning av värdepapper'),
(718, NULL, 'Förändring av lager av värdepapper', NULL, NULL, '4988', 'Återföring av nedskrivning av värdepapper'),
(719, '5', 'Övriga externa rörelseutgifter/ kostnader', NULL, NULL, NULL, NULL),
(720, '50', 'Lokalkostnader', NULL, NULL, NULL, NULL),
(721, '500', 'Lokalkostnader (gruppkonto)', NULL, NULL, '5000', 'Lokalkostnader (gruppkonto)'),
(722, '501', 'Lokalhyra', NULL, '1', '5010', 'Lokalhyra'),
(723, NULL, 'Lokalhyra', NULL, NULL, '5011', 'Hyra för kontorslokaler'),
(724, NULL, 'Lokalhyra', NULL, NULL, '5012', 'Hyra för garage'),
(725, NULL, 'Lokalhyra', NULL, NULL, '5013', 'Hyra för lagerlokaler'),
(726, '502', 'El för belysning', NULL, '1', '5020', 'El för belysning'),
(727, '503', 'Värme', NULL, '1', '5030', 'Värme'),
(728, '504', 'Vatten och avlopp', NULL, '1', '5040', 'Vatten och avlopp'),
(729, '505', 'Lokaltillbehör', NULL, NULL, '5050', 'Lokaltillbehör'),
(730, '506', 'Städning och renhållning', NULL, '1', '5060', 'Städning och renhållning'),
(731, NULL, 'Städning och renhållning', NULL, NULL, '5061', 'Städning'),
(732, NULL, 'Städning och renhållning', NULL, NULL, '5062', 'Sophämtning'),
(733, NULL, 'Städning och renhållning', NULL, NULL, '5063', 'Hyra för sopcontainer'),
(734, NULL, 'Städning och renhållning', NULL, NULL, '5064', 'Snöröjning'),
(735, NULL, 'Städning och renhållning', NULL, NULL, '5065', 'Trädgårdsskötsel'),
(736, '507', 'Reparation och underhåll av lokaler', NULL, '1', '5070', 'Reparation och underhåll av lokaler'),
(737, '509', 'Övriga lokalkostnader', NULL, NULL, '5090', 'Övriga lokalkostnader'),
(738, NULL, 'Övriga lokalkostnader', NULL, NULL, '5098', 'Övriga lokalkostnader, avdragsgilla'),
(739, NULL, 'Övriga lokalkostnader', NULL, NULL, '5099', 'Övriga lokalkostnader, ej avdragsgilla'),
(740, '51', 'Fastighetskostnader', NULL, NULL, NULL, NULL),
(741, '510', 'Fastighetskostnader (gruppkonto)', NULL, NULL, '5100', 'Fastighetskostnader (gruppkonto)'),
(742, '511', 'Tomträttsavgäld/arrende', NULL, NULL, '5110', 'Tomträttsavgäld/arrende'),
(743, '512', 'El för belysning', NULL, '1', '5120', 'El för belysning'),
(744, '513', 'Värme', NULL, '1', '5130', 'Värme'),
(745, NULL, 'Värme', NULL, NULL, '5131', 'Uppvärmning'),
(746, NULL, 'Värme', NULL, NULL, '5132', 'Sotning'),
(747, '514', 'Vatten och avlopp', NULL, '1', '5140', 'Vatten och avlopp'),
(748, '516', 'Städning och renhållning', NULL, '1', '5160', 'Städning och renhållning'),
(749, NULL, 'Städning och renhållning', NULL, NULL, '5161', 'Städning'),
(750, NULL, 'Städning och renhållning', NULL, NULL, '5162', 'Sophämtning'),
(751, NULL, 'Städning och renhållning', NULL, NULL, '5163', 'Hyra för sopcontainer'),
(752, NULL, 'Städning och renhållning', NULL, NULL, '5164', 'Snöröjning'),
(753, NULL, 'Städning och renhållning', NULL, NULL, '5165', 'Trädgårdsskötsel'),
(754, '517', 'Reparation och underhåll av fastighet', NULL, '1', '5170', 'Reparation och underhåll av fastighet'),
(755, '519', 'Övriga fastighetskostnader', NULL, NULL, '5190', 'Övriga fastighetskostnader'),
(756, NULL, 'Övriga fastighetskostnader', NULL, NULL, '5191', 'Fastighetsskatt/fastighetsavgift'),
(757, NULL, 'Övriga fastighetskostnader', NULL, NULL, '5192', 'Fastighetsförsäkringspremier'),
(758, NULL, 'Övriga fastighetskostnader', NULL, NULL, '5193', 'Fastighetsskötsel och förvaltning'),
(759, NULL, 'Övriga fastighetskostnader', NULL, NULL, '5198', 'Övriga fastighetskostnader, avdragsgilla'),
(760, NULL, 'Övriga fastighetskostnader', NULL, NULL, '5199', 'Övriga fastighetskostnader, ej avdragsgilla'),
(761, '52', 'Hyra av anläggningstillgångar', NULL, NULL, NULL, NULL),
(762, '520', 'Hyra av anläggningstillgångar (gruppkonto)', NULL, '1', '5200', 'Hyra av anläggningstillgångar (gruppkonto)'),
(763, '521', 'Hyra av maskiner och andra tekniska anläggningar', NULL, NULL, '5210', 'Hyra av maskiner och andra tekniska anläggningar'),
(764, NULL, 'Hyra av maskiner och andra tekniska anläggningar', NULL, NULL, '5211', 'Korttidshyra av maskiner och andra tekniska anläggningar'),
(765, NULL, 'Hyra av maskiner och andra tekniska anläggningar', NULL, NULL, '5212', 'Leasing av maskiner och andra tekniska anläggningar'),
(766, '522', 'Hyra av inventarier och verktyg', NULL, NULL, '5220', 'Hyra av inventarier och verktyg'),
(767, NULL, 'Hyra av inventarier och verktyg', NULL, NULL, '5221', 'Korttidshyra av inventarier och verktyg'),
(768, NULL, 'Hyra av inventarier och verktyg', NULL, NULL, '5222', 'Leasing av inventarier och verktyg'),
(769, '525', 'Hyra av datorer', NULL, NULL, '5250', 'Hyra av datorer'),
(770, NULL, 'Hyra av datorer', NULL, NULL, '5251', 'Korttidshyra av datorer'),
(771, NULL, 'Hyra av datorer', NULL, NULL, '5252', 'Leasing av datorer'),
(772, '529', 'Övriga hyreskostnader för anläggningstillgångar', NULL, NULL, '5290', 'Övriga hyreskostnader för anläggningstillgångar'),
(773, '53', 'Energikostnader', NULL, NULL, NULL, NULL),
(774, '530', 'Energikostnader (gruppkonto)', NULL, '1', '5300', 'Energikostnader (gruppkonto)'),
(775, '531', 'El för drift', NULL, NULL, '5310', 'El för drift'),
(776, '532', 'Gas', NULL, NULL, '5320', 'Gas'),
(777, '533', 'Eldningsolja', NULL, NULL, '5330', 'Eldningsolja'),
(778, '534', 'Stenkol och koks', NULL, NULL, '5340', 'Stenkol och koks'),
(779, '535', 'Torv, träkol, ved och annat träbränsle', NULL, NULL, '5350', 'Torv, träkol, ved och annat träbränsle'),
(780, '536', 'Bensin, fotogen och motorbrännolja', NULL, NULL, '5360', 'Bensin, fotogen och motorbrännolja'),
(781, '537', 'Fjärrvärme, kyla och ånga', NULL, NULL, '5370', 'Fjärrvärme, kyla och ånga'),
(782, '538', 'Vatten', NULL, NULL, '5380', 'Vatten'),
(783, '539', 'Övriga energikostnader', NULL, NULL, '5390', 'Övriga energikostnader'),
(784, '54', 'Förbrukningsinventarier och förbrukningsmaterial', NULL, NULL, NULL, NULL),
(785, '540', 'Förbrukningsinventarier och förbrukningsmaterial (gruppkonto)', NULL, NULL, '5400', 'Förbrukningsinventarier och förbrukningsmaterial (gruppkonto)'),
(786, '541', 'Förbrukningsinventarier', NULL, '1', '5410', 'Förbrukningsinventarier'),
(787, NULL, 'Förbrukningsinventarier', NULL, NULL, '5411', 'Förbrukningsinventarier med en livslängd på mer än ett år'),
(788, NULL, 'Förbrukningsinventarier', NULL, NULL, '5412', 'Förbrukningsinventarier med en livslängd på ett år eller mindre'),
(789, '542', 'Programvaror', NULL, '1', '5420', 'Programvaror'),
(790, '543', 'Transportinventarier', NULL, NULL, '5430', 'Transportinventarier'),
(791, '544', 'Förbrukningsemballage', NULL, NULL, '5440', 'Förbrukningsemballage'),
(792, '546', 'Förbrukningsmaterial', NULL, '1', '5460', 'Förbrukningsmaterial'),
(793, '548', 'Arbetskläder och skyddsmaterial', NULL, NULL, '5480', 'Arbetskläder och skyddsmaterial'),
(794, '549', 'Övriga förbrukningsinventarier och förbrukningsmaterial', NULL, NULL, '5490', 'Övriga förbrukningsinventarier och förbrukningsmaterial'),
(795, NULL, 'Övriga förbrukningsinventarier och förbrukningsmaterial', NULL, NULL, '5491', 'Övriga förbrukningsinventarier med en livslängd på mer än ett år'),
(796, NULL, 'Övriga förbrukningsinventarier och förbrukningsmaterial', NULL, NULL, '5492', 'Övriga förbrukningsinventarier med en livslängd på ett år eller mindre'),
(797, NULL, 'Övriga förbrukningsinventarier och förbrukningsmaterial', NULL, NULL, '5493', 'Övrigt förbrukningsmaterial'),
(798, '55', 'Reparation och underhåll', NULL, NULL, NULL, NULL),
(799, '550', 'Reparation och underhåll (gruppkonto)', NULL, '1', '5500', 'Reparation och underhåll (gruppkonto)'),
(800, '551', 'Reparation och underhåll av maskiner och andra tekniska anläggningar', NULL, NULL, '5510', 'Reparation och underhåll av maskiner och andra tekniska anläggningar'),
(801, '552', 'Reparation och underhåll av inventarier, verktyg och datorer m.m.', NULL, NULL, '5520', 'Reparation och underhåll av inventarier, verktyg och datorer m.m.'),
(802, '553', 'Reparation och underhåll av installationer', NULL, NULL, '5530', 'Reparation och underhåll av installationer'),
(803, '555', 'Reparation och underhåll av förbrukningsinventarier', NULL, NULL, '5550', 'Reparation och underhåll av förbrukningsinventarier'),
(804, '558', 'Underhåll och tvätt av arbetskläder', NULL, NULL, '5580', 'Underhåll och tvätt av arbetskläder'),
(805, '559', 'Övriga kostnader för reparation och underhåll', NULL, NULL, '5590', 'Övriga kostnader för reparation och underhåll'),
(806, '56', 'Kostnader för transportmedel', NULL, NULL, NULL, NULL),
(807, '560', 'Kostnader för transportmedel (gruppkonto)', NULL, '1', '5600', 'Kostnader för transportmedel (gruppkonto)'),
(808, '561', 'Personbilskostnader', NULL, NULL, '5610', 'Personbilskostnader'),
(809, NULL, 'Personbilskostnader', NULL, '1', '5611', 'Drivmedel för personbilar'),
(810, NULL, 'Personbilskostnader', NULL, '1', '5612', 'Försäkring och skatt för personbilar'),
(811, NULL, 'Personbilskostnader', NULL, '1', '5613', 'Reparation och underhåll av personbilar'),
(812, NULL, 'Personbilskostnader', NULL, '1', '5615', 'Leasing av personbilar'),
(813, NULL, 'Personbilskostnader', NULL, NULL, '5616', 'Trängselskatt, avdragsgill'),
(814, NULL, 'Personbilskostnader', NULL, NULL, '5619', 'Övriga personbilskostnader'),
(815, '562', 'Lastbilskostnader', NULL, NULL, '5620', 'Lastbilskostnader'),
(816, '563', 'Truckkostnader', NULL, NULL, '5630', 'Truckkostnader'),
(817, '564', 'Kostnader för arbetsmaskiner', NULL, NULL, '5640', 'Kostnader för arbetsmaskiner'),
(818, '565', 'Traktorkostnader', NULL, NULL, '5650', 'Traktorkostnader'),
(819, '566', 'Motorcykel-, moped- och skoterkostnader', NULL, NULL, '5660', 'Motorcykel-, moped- och skoterkostnader'),
(820, '567', 'Båt-, flygplans- och helikopterkostnader', NULL, NULL, '5670', 'Båt-, flygplans- och helikopterkostnader'),
(821, '569', 'Övriga kostnader för transportmedel', NULL, NULL, '5690', 'Övriga kostnader för transportmedel'),
(822, '57', 'Frakter och transporter', NULL, NULL, NULL, NULL),
(823, '570', 'Frakter och transporter (gruppkonto)', NULL, '1', '5700', 'Frakter och transporter (gruppkonto)'),
(824, '571', 'Frakter, transporter och försäkringar vid varudistribution', NULL, NULL, '5710', 'Frakter, transporter och försäkringar vid varudistribution'),
(825, '572', 'Tull- och speditionskostnader m.m.', NULL, NULL, '5720', 'Tull- och speditionskostnader m.m.'),
(826, '573', 'Arbetstransporter', NULL, NULL, '5730', 'Arbetstransporter'),
(827, '579', 'Övriga kostnader för frakter och transporter', NULL, NULL, '5790', 'Övriga kostnader för frakter och transporter'),
(828, '58', 'Resekostnader', NULL, NULL, NULL, NULL),
(829, '580', 'Resekostnader (gruppkonto)', NULL, '1', '5800', 'Resekostnader (gruppkonto)'),
(830, '581', 'Biljetter', NULL, '1', '5810', 'Biljetter'),
(831, '582', 'Hyrbilskostnader', NULL, '1', '5820', 'Hyrbilskostnader'),
(832, '583', 'Kost och logi', NULL, NULL, '5830', 'Kost och logi'),
(833, NULL, 'Kost och logi', NULL, '1', '5831', 'Kost och logi i Sverige'),
(834, NULL, 'Kost och logi', NULL, '1', '5832', 'Kost och logi i utlandet'),
(835, '589', 'Övriga resekostnader', NULL, NULL, '5890', 'Övriga resekostnader'),
(836, '59', 'Reklam och PR', NULL, NULL, NULL, NULL),
(837, '590', 'Reklam och PR (gruppkonto)', NULL, '1', '5900', 'Reklam och PR (gruppkonto)'),
(838, '591', 'Annonsering', NULL, NULL, '5910', 'Annonsering'),
(839, '592', 'Utomhus- och trafikreklam', NULL, NULL, '5920', 'Utomhus- och trafikreklam'),
(840, '593', 'Reklamtrycksaker och direktreklam', NULL, NULL, '5930', 'Reklamtrycksaker och direktreklam'),
(841, '594', 'Utställningar och mässor', NULL, NULL, '5940', 'Utställningar och mässor'),
(842, '595', 'Butiksreklam och återförsäljarreklam', NULL, NULL, '5950', 'Butiksreklam och återförsäljarreklam'),
(843, '596', 'Varuprover, reklamgåvor, presentreklam och tävlingar', NULL, NULL, '5960', 'Varuprover, reklamgåvor, presentreklam och tävlingar'),
(844, '597', 'Film-, radio-, TV- och Internetreklam', NULL, NULL, '5970', 'Film-, radio-, TV- och Internetreklam'),
(845, '598', 'PR, institutionell reklam och sponsring', NULL, NULL, '5980', 'PR, institutionell reklam och sponsring'),
(846, '599', 'Övriga kostnader för reklam och PR', NULL, NULL, '5990', 'Övriga kostnader för reklam och PR'),
(847, '6', 'Övriga externa rörelseutgifter/ kostnader', NULL, NULL, NULL, NULL),
(848, '60', 'Övriga försäljningskostnader', NULL, NULL, NULL, NULL),
(849, '600', 'Övriga försäljningskostnader (gruppkonto)', NULL, NULL, '6000', 'Övriga försäljningskostnader (gruppkonto)'),
(850, '601', 'Kataloger, prislistor m.m.', NULL, NULL, '6010', 'Kataloger, prislistor m.m.'),
(851, '602', 'Egna facktidskrifter', NULL, NULL, '6020', 'Egna facktidskrifter'),
(852, '603', 'Speciella orderkostnader', NULL, NULL, '6030', 'Speciella orderkostnader'),
(853, '604', 'Kontokortsavgifter', NULL, NULL, '6040', 'Kontokortsavgifter'),
(854, '605', 'Försäljningsprovisioner', NULL, NULL, '6050', 'Försäljningsprovisioner'),
(855, NULL, NULL, NULL, NULL, '6055', 'Franchisekostnader o.dyl.'),
(856, '606', 'Kreditförsäljningskostnader', NULL, NULL, '6060', 'Kreditförsäljningskostnader'),
(857, NULL, 'Kreditförsäljningskostnader', NULL, NULL, '6061', 'Kreditupplysning'),
(858, NULL, 'Kreditförsäljningskostnader', NULL, NULL, '6062', 'Inkasso och KFM-avgifter'),
(859, NULL, 'Kreditförsäljningskostnader', NULL, NULL, '6063', 'Kreditförsäkringspremier'),
(860, NULL, 'Kreditförsäljningskostnader', NULL, NULL, '6064', 'Factoringavgifter'),
(861, NULL, 'Kreditförsäljningskostnader', NULL, NULL, '6069', 'Övriga kreditförsäljningskostnader'),
(862, '607', 'Representation', NULL, NULL, '6070', 'Representation'),
(863, NULL, 'Representation', NULL, '1', '6071', 'Representation, avdragsgill'),
(864, NULL, 'Representation', NULL, '1', '6072', 'Representation, ej avdragsgill'),
(865, '608', 'Bankgarantier', NULL, NULL, '6080', 'Bankgarantier'),
(866, '609', 'Övriga försäljningskostnader', NULL, '1', '6090', 'Övriga försäljningskostnader'),
(867, '61', 'Kontorsmateriel och trycksaker', NULL, NULL, NULL, NULL),
(868, '610', 'Kontorsmateriel och trycksaker (gruppkonto)', NULL, '1', '6100', 'Kontorsmateriel och trycksaker (gruppkonto)'),
(869, '611', 'Kontorsmateriel', NULL, NULL, '6110', 'Kontorsmateriel'),
(870, '615', 'Trycksaker', NULL, NULL, '6150', 'Trycksaker'),
(871, '62', 'Tele och post', NULL, NULL, NULL, NULL),
(872, '620', 'Tele och post (gruppkonto)', NULL, NULL, '6200', 'Tele och post (gruppkonto)'),
(873, '621', 'Telekommunikation', NULL, '1', '6210', 'Telekommunikation'),
(874, NULL, 'Telekommunikation', NULL, NULL, '6211', 'Fast telefoni'),
(875, NULL, 'Telekommunikation', NULL, NULL, '6212', 'Mobiltelefon'),
(876, NULL, 'Telekommunikation', NULL, NULL, '6213', 'Mobilsökning'),
(877, NULL, 'Telekommunikation', NULL, NULL, '6214', 'Fax'),
(878, NULL, 'Telekommunikation', NULL, NULL, '6215', 'Telex'),
(879, '623', 'Datakommunikation', NULL, NULL, '6230', 'Datakommunikation'),
(880, '625', 'Postbefordran', NULL, '1', '6250', 'Postbefordran'),
(881, '63', 'Företagsförsäkringar och övriga riskkostnader', NULL, NULL, NULL, NULL),
(882, '630', 'Företagsförsäkringar och övriga riskkostnader (gruppkonto)', NULL, NULL, '6300', 'Företagsförsäkringar och övriga riskkostnader (gruppkonto)'),
(883, '631', 'Företagsförsäkringar', NULL, '1', '6310', 'Företagsförsäkringar'),
(884, '632', 'Självrisker vid skada', NULL, NULL, '6320', 'Självrisker vid skada'),
(885, '633', 'Förluster i pågående arbeten', NULL, NULL, '6330', 'Förluster i pågående arbeten'),
(886, '634', 'Lämnade skadestånd', NULL, NULL, '6340', 'Lämnade skadestånd'),
(887, NULL, 'Lämnade skadestånd', NULL, NULL, '6341', 'Lämnade skadestånd, avdragsgilla'),
(888, NULL, 'Lämnade skadestånd', NULL, NULL, '6342', 'Lämnade skadestånd, ej avdragsgilla'),
(889, '635', 'Förluster på kundfordringar', NULL, '1', '6350', 'Förluster på kundfordringar'),
(890, NULL, 'Förluster på kundfordringar', NULL, NULL, '6351', 'Konstaterade förluster på kundfordringar'),
(891, NULL, 'Förluster på kundfordringar', NULL, NULL, '6352', 'Befarade förluster på kundfordringar'),
(892, '636', 'Garantikostnader', NULL, NULL, '6360', 'Garantikostnader'),
(893, NULL, 'Garantikostnader', NULL, NULL, '6361', 'Förändring av garantiavsättning'),
(894, NULL, 'Garantikostnader', NULL, NULL, '6362', 'Faktiska garantikostnader'),
(895, '637', 'Kostnader för bevakning och larm', NULL, NULL, '6370', 'Kostnader för bevakning och larm'),
(896, '638', 'Förluster på övriga kortfristiga fordringar', NULL, NULL, '6380', 'Förluster på övriga kortfristiga fordringar'),
(897, '639', 'Övriga riskkostnader', NULL, '1', '6390', 'Övriga riskkostnader'),
(898, '64', 'Förvaltningskostnader', NULL, NULL, NULL, NULL),
(899, '640', 'Förvaltningskostnader (gruppkonto)', NULL, NULL, '6400', 'Förvaltningskostnader (gruppkonto)'),
(900, '641', 'Styrelsearvoden som inte är lön', NULL, '1', '6410', 'Styrelsearvoden som inte är lön'),
(901, '642', 'Ersättningar till revisor', NULL, '1', '6420', 'Ersättningar till revisor'),
(902, NULL, 'Ersättningar till revisor', NULL, NULL, '6421', 'Revision'),
(903, NULL, 'Ersättningar till revisor', NULL, NULL, '6422', 'Revisonsverksamhet utöver revision'),
(904, NULL, 'Ersättningar till revisor', NULL, NULL, '6423', 'Skatterådgivning – revisor'),
(905, NULL, 'Ersättningar till revisor', NULL, NULL, '6424', 'Övriga tjänster – revisor'),
(906, '643', 'Management fees', NULL, NULL, '6430', 'Management fees'),
(907, '644', 'Årsredovisning och delårsrapporter', NULL, NULL, '6440', 'Årsredovisning och delårsrapporter'),
(908, '645', 'Bolagsstämma/års- eller föreningsstämma', NULL, NULL, '6450', 'Bolagsstämma/års- eller föreningsstämma'),
(909, '649', 'Övriga förvaltningskostnader', NULL, NULL, '6490', 'Övriga förvaltningskostnader'),
(910, '65', 'Övriga externa tjänster', NULL, NULL, NULL, NULL),
(911, '650', 'Övriga externa tjänster (gruppkonto)', NULL, NULL, '6500', 'Övriga externa tjänster (gruppkonto)'),
(912, '651', 'Mätningskostnader', NULL, NULL, '6510', 'Mätningskostnader'),
(913, '652', 'Ritnings- och kopieringskostnader', NULL, NULL, '6520', 'Ritnings- och kopieringskostnader'),
(914, '653', 'Redovisningstjänster', NULL, '1', '6530', 'Redovisningstjänster'),
(915, '654', 'IT-tjänster', NULL, '1', '6540', 'IT-tjänster'),
(916, '655', 'Konsultarvoden', NULL, '1', '6550', 'Konsultarvoden'),
(917, NULL, 'Konsultarvoden', NULL, NULL, '6551', 'Arkitekttjänster'),
(918, NULL, 'Konsultarvoden', NULL, NULL, '6552', 'Teknisk provning och analys'),
(919, NULL, 'Konsultarvoden', NULL, NULL, '6553', 'Tekniska konsulttjänster'),
(920, NULL, 'Konsultarvoden', NULL, NULL, '6554', 'Finansiell- och övrig ekonomisk rådgivning'),
(921, NULL, 'Konsultarvoden', NULL, NULL, '6555', 'Skatterådgivning inkl. insolvens- och konkursförvaltning'),
(922, NULL, 'Konsultarvoden', NULL, NULL, '6556', 'Köpta tjänster avseende forskning och utveckling'),
(923, NULL, 'Konsultarvoden', NULL, NULL, '6559', 'Övrig konsultverksamhet'),
(924, '656', 'Serviceavgifter till branschorganisationer', NULL, '1', '6560', 'Serviceavgifter till branschorganisationer'),
(925, '657', 'Bankkostnader', NULL, '1', '6570', 'Bankkostnader'),
(926, '658', 'Advokat- och rättegångskostnader', NULL, NULL, '6580', 'Advokat- och rättegångskostnader'),
(927, '659', 'Övriga externa tjänster', NULL, '1', '6590', 'Övriga externa tjänster'),
(928, '66', '(Fri kontogrupp)', NULL, NULL, NULL, NULL),
(929, '67', '(Fri kontogrupp)', NULL, NULL, NULL, NULL),
(930, '68', 'Inhyrd personal', NULL, NULL, NULL, NULL),
(931, '680', 'Inhyrd personal (gruppkonto)', NULL, '1', '6800', 'Inhyrd personal (gruppkonto)'),
(932, '681', 'Inhyrd produktionspersonal', NULL, NULL, '6810', 'Inhyrd produktionspersonal'),
(933, '682', 'Inhyrd lagerpersonal', NULL, NULL, '6820', 'Inhyrd lagerpersonal'),
(934, '683', 'Inhyrd transportpersonal', NULL, NULL, '6830', 'Inhyrd transportpersonal'),
(935, '684', 'Inhyrd kontors- och ekonomipersonal', NULL, NULL, '6840', 'Inhyrd kontors- och ekonomipersonal'),
(936, '685', 'Inhyrd IT-personal', NULL, NULL, '6850', 'Inhyrd IT-personal'),
(937, '686', 'Inhyrd marknads- och försäljningspersonal', NULL, NULL, '6860', 'Inhyrd marknads- och försäljningspersonal'),
(938, '687', 'Inhyrd restaurang- och butikspersonal', NULL, NULL, '6870', 'Inhyrd restaurang- och butikspersonal'),
(939, '688', 'Inhyrda företagsledare', NULL, NULL, '6880', 'Inhyrda företagsledare'),
(940, '689', 'Övrig inhyrd personal', NULL, NULL, '6890', 'Övrig inhyrd personal'),
(941, '69', 'Övriga externa kostnader', NULL, NULL, NULL, NULL),
(942, '690', 'Övriga externa kostnader (gruppkonto)', NULL, NULL, '6900', 'Övriga externa kostnader (gruppkonto)'),
(943, '691', 'Licensavgifter och royalties', NULL, NULL, '6910', 'Licensavgifter och royalties'),
(944, '692', 'Kostnader för egna patent', NULL, NULL, '6920', 'Kostnader för egna patent'),
(945, '693', 'Kostnader för varumärken m.m.', NULL, NULL, '6930', 'Kostnader för varumärken m.m.'),
(946, '694', 'Kontroll-, provnings- och stämpelavgifter', NULL, NULL, '6940', 'Kontroll-, provnings- och stämpelavgifter'),
(947, '695', 'Tillsynsavgifter myndigheter', NULL, NULL, '6950', 'Tillsynsavgifter myndigheter'),
(948, '697', 'Tidningar, tidskrifter och facklitteratur', NULL, '1', '6970', 'Tidningar, tidskrifter och facklitteratur'),
(949, '698', 'Föreningsavgifter', NULL, '1', '6980', 'Föreningsavgifter'),
(950, NULL, 'Föreningsavgifter', NULL, NULL, '6981', 'Föreningsavgifter, avdragsgilla'),
(951, NULL, 'Föreningsavgifter', NULL, NULL, '6982', 'Föreningsavgifter, ej avdragsgilla'),
(952, '699', 'Övriga externa kostnader', NULL, NULL, '6990', 'Övriga externa kostnader'),
(953, NULL, 'Övriga externa kostnader', NULL, '1', '6991', 'Övriga externa kostnader, avdragsgilla'),
(954, NULL, 'Övriga externa kostnader', NULL, '1', '6992', 'Övriga externa kostnader, ej avdragsgilla'),
(955, NULL, 'Övriga externa kostnader', NULL, NULL, '6993', 'Lämnade bidrag och gåvor'),
(956, NULL, 'Övriga externa kostnader', NULL, NULL, '6996', 'Betald utländsk inkomstskatt'),
(957, NULL, 'Övriga externa kostnader', NULL, NULL, '6997', 'Obetald utländsk inkomstskatt'),
(958, NULL, 'Övriga externa kostnader', NULL, NULL, '6998', 'Utländsk moms'),
(959, NULL, 'Övriga externa kostnader', NULL, NULL, '6999', 'Ingående moms, blandad verksamhet'),
(960, '7', 'Utgifter/kostnader för personal, avskrivningar m.m.', NULL, NULL, NULL, NULL),
(961, '70', 'Löner till kollektivanställda', NULL, NULL, NULL, NULL),
(962, '700', 'Löner till kollektivanställda (gruppkonto)', NULL, NULL, '7000', 'Löner till kollektivanställda (gruppkonto)'),
(963, '701', 'Löner till kollektivanställda', NULL, '1', '7010', 'Löner till kollektivanställda'),
(964, NULL, 'Löner till kollektivanställda', NULL, NULL, '7011', 'Löner till kollektivanställda'),
(965, NULL, 'Löner till kollektivanställda', NULL, NULL, '7012', 'Vinstandelar till kollektivanställda'),
(966, NULL, 'Löner till kollektivanställda', NULL, NULL, '7013', 'Lön växa-stöd kollektivanställda 10,21 %'),
(967, NULL, 'Löner till kollektivanställda', NULL, NULL, '7017', 'Avgångsvederlag till kollektivanställda'),
(968, NULL, 'Löner till kollektivanställda', NULL, NULL, '7018', 'Bruttolöneavdrag, kollektivanställda'),
(969, NULL, 'Löner till kollektivanställda', NULL, NULL, '7019', 'Upplupna löner och vinstandelar till kollektivanställda'),
(970, '703', 'Löner till kollektivanställda (utlandsanställda)', NULL, NULL, '7030', 'Löner till kollektivanställda (utlandsanställda)'),
(971, NULL, 'Löner till kollektivanställda (utlandsanställda)', NULL, NULL, '7031', 'Löner till kollektivanställda (utlandsanställda)'),
(972, NULL, 'Löner till kollektivanställda (utlandsanställda)', NULL, NULL, '7032', 'Vinstandelar till kollektivanställda (utlandsanställda)'),
(973, NULL, 'Löner till kollektivanställda (utlandsanställda)', NULL, NULL, '7037', 'Avgångsvederlag till kollektivanställda (utlandsanställda)'),
(974, NULL, 'Löner till kollektivanställda (utlandsanställda)', NULL, NULL, '7038', 'Bruttolöneavdrag, kollektivanställda (utlandsanställda)'),
(975, NULL, 'Löner till kollektivanställda (utlandsanställda)', NULL, NULL, '7039', 'Upplupna löner och vinstandelar till kollektivanställda (utlandsanställda)'),
(976, '708', 'Löner till kollektivanställda för ej arbetad tid', NULL, NULL, '7080', 'Löner till kollektivanställda för ej arbetad tid'),
(977, NULL, 'Löner till kollektivanställda för ej arbetad tid', NULL, NULL, '7081', 'Sjuklöner till kollektivanställda'),
(978, NULL, 'Löner till kollektivanställda för ej arbetad tid', NULL, NULL, '7082', 'Semesterlöner till kollektivanställda'),
(979, NULL, 'Löner till kollektivanställda för ej arbetad tid', NULL, NULL, '7083', 'Föräldraersättning till kollektivanställda'),
(980, NULL, 'Löner till kollektivanställda för ej arbetad tid', NULL, NULL, '7089', 'Övriga löner till kollektivanställda för ej arbetad tid'),
(981, '709', 'Förändring av semesterlöneskuld', NULL, '1', '7090', 'Förändring av semesterlöneskuld'),
(982, '71', '(Fri kontogrupp)', NULL, NULL, NULL, NULL),
(983, '72', 'Löner till tjänstemän och företagsledare', NULL, NULL, NULL, NULL),
(984, '720', 'Löner till tjänstemän och företagsledare (gruppkonto)', NULL, NULL, '7200', 'Löner till tjänstemän och företagsledare (gruppkonto)'),
(985, '721', 'Löner till tjänstemän', NULL, '1', '7210', 'Löner till tjänstemän'),
(986, NULL, 'Löner till tjänstemän', NULL, NULL, '7211', 'Löner till tjänstemän'),
(987, NULL, 'Löner till tjänstemän', NULL, NULL, '7212', 'Vinstandelar till tjänstemän'),
(988, NULL, 'Löner till tjänstemän', NULL, NULL, '7213', 'Lön växa-stöd tjänstemän 10,21 %'),
(989, NULL, 'Löner till tjänstemän', NULL, NULL, '7217', 'Avgångsvederlag till tjänstemän'),
(990, NULL, 'Löner till tjänstemän', NULL, NULL, '7218', 'Bruttolöneavdrag, tjänstemän'),
(991, NULL, 'Löner till tjänstemän', NULL, NULL, '7219', 'Upplupna löner och vinstandelar till tjänstemän'),
(992, '722', 'Löner till företagsledare', NULL, '1', '7220', 'Löner till företagsledare'),
(993, NULL, 'Löner till företagsledare', NULL, NULL, '7221', 'Löner till företagsledare');
INSERT INTO `chart_of_accounts` (`id`, `main_account`, `main_account_description`, `no_k2`, `simple_account`, `sub_account`, `sub_account_description`) VALUES
(994, NULL, 'Löner till företagsledare', NULL, NULL, '7222', 'Tantiem till företagsledare'),
(995, NULL, 'Löner till företagsledare', NULL, NULL, '7227', 'Avgångsvederlag till företagsledare'),
(996, NULL, 'Löner till företagsledare', NULL, NULL, '7228', 'Bruttolöneavdrag, företagsledare'),
(997, NULL, 'Löner till företagsledare', NULL, NULL, '7229', 'Upplupna löner och tantiem till företagsledare'),
(998, '723', 'Löner till tjänstemän och ftgsledare (utlandsanställda)', NULL, NULL, '7230', 'Löner till tjänstemän och ftgsledare (utlandsanställda)'),
(999, NULL, 'Löner till tjänstemän och ftgsledare (utlandsanställda)', NULL, NULL, '7231', 'Löner till tjänstemän och ftgsledare (utlandsanställda)'),
(1000, NULL, 'Löner till tjänstemän och ftgsledare (utlandsanställda)', NULL, NULL, '7232', 'Vinstandelar till tjänstemän och ftgsledare (utlandsanställda)'),
(1001, NULL, 'Löner till tjänstemän och ftgsledare (utlandsanställda)', NULL, NULL, '7237', 'Avgångsvederlag till tjänstemän och ftgsledare (utlandsanställda)'),
(1002, NULL, 'Löner till tjänstemän och ftgsledare (utlandsanställda)', NULL, NULL, '7238', 'Bruttolöneavdrag, tjänstemän och ftgsledare (utlandsanställda)'),
(1003, NULL, 'Löner till tjänstemän och ftgsledare (utlandsanställda)', NULL, NULL, '7239', 'Upplupna löner och vinstandelar till tjänstemän och ftgsledare (utlandsanställda)'),
(1004, '724', 'Styrelsearvoden', NULL, '1', '7240', 'Styrelsearvoden'),
(1005, '728', 'Löner till tjänstemän och företagsledare för ej arbetad tid', NULL, NULL, '7280', 'Löner till tjänstemän och företagsledare för ej arbetad tid'),
(1006, NULL, 'Löner till tjänstemän och företagsledare för ej arbetad tid', NULL, NULL, '7281', 'Sjuklöner till tjänstemän'),
(1007, NULL, 'Löner till tjänstemän och företagsledare för ej arbetad tid', NULL, NULL, '7282', 'Sjuklöner till företagsledare'),
(1008, NULL, 'Löner till tjänstemän och företagsledare för ej arbetad tid', NULL, NULL, '7283', 'Föräldraersättning till tjänstemän'),
(1009, NULL, 'Löner till tjänstemän och företagsledare för ej arbetad tid', NULL, NULL, '7284', 'Föräldraersättning till företagsledare'),
(1010, NULL, 'Löner till tjänstemän och företagsledare för ej arbetad tid', NULL, NULL, '7285', 'Semesterlöner till tjänstemän'),
(1011, NULL, 'Löner till tjänstemän och företagsledare för ej arbetad tid', NULL, NULL, '7286', 'Semesterlöner till företagsledare'),
(1012, NULL, 'Löner till tjänstemän och företagsledare för ej arbetad tid', NULL, NULL, '7288', 'Övriga löner till tjänstemän för ej arbetad tid'),
(1013, NULL, 'Löner till tjänstemän och företagsledare för ej arbetad tid', NULL, NULL, '7289', 'Övriga löner till företagsledare för ej arbetad tid'),
(1014, '729', 'Förändring av semesterlöneskuld', NULL, '1', '7290', 'Förändring av semesterlöneskuld'),
(1015, NULL, 'Förändring av semesterlöneskuld', NULL, NULL, '7291', 'Förändring av semesterlöneskuld till tjänstemän'),
(1016, NULL, 'Förändring av semesterlöneskuld', NULL, NULL, '7292', 'Förändring av semesterlöneskuld till företagsledare'),
(1017, '73', 'Kostnadsersättningar och förmåner', NULL, NULL, NULL, NULL),
(1018, '730', 'Kostnadsersättningar och förmåner (gruppkonto)', NULL, NULL, '7300', 'Kostnadsersättningar och förmåner (gruppkonto)'),
(1019, '731', 'Kontanta extraersättningar', NULL, '1', '7310', 'Kontanta extraersättningar'),
(1020, NULL, 'Kontanta extraersättningar', NULL, NULL, '7311', 'Ersättningar för sammanträden m.m.'),
(1021, NULL, 'Kontanta extraersättningar', NULL, NULL, '7312', 'Ersättningar för förslagsverksamhet och uppfinningar'),
(1022, NULL, 'Kontanta extraersättningar', NULL, NULL, '7313', 'Ersättningar för/bidrag till bostadskostnader'),
(1023, NULL, 'Kontanta extraersättningar', NULL, NULL, '7314', 'Ersättningar för/bidrag till måltidskostnader'),
(1024, NULL, 'Kontanta extraersättningar', NULL, NULL, '7315', 'Ersättningar för/bidrag till resor till och från arbetsplatsen'),
(1025, NULL, 'Kontanta extraersättningar', NULL, NULL, '7316', 'Ersättningar för/bidrag till arbetskläder'),
(1026, NULL, 'Kontanta extraersättningar', NULL, NULL, '7317', 'Ersättningar för/bidrag till arbetsmaterial och arbetsverktyg'),
(1027, NULL, 'Kontanta extraersättningar', NULL, NULL, '7318', 'Felräkningspengar'),
(1028, NULL, 'Kontanta extraersättningar', NULL, NULL, '7319', 'Övriga kontanta extraersättningar'),
(1029, '732', 'Traktamenten vid tjänsteresa', NULL, NULL, '7320', 'Traktamenten vid tjänsteresa'),
(1030, NULL, 'Traktamenten vid tjänsteresa', NULL, '1', '7321', 'Skattefria traktamenten, Sverige'),
(1031, NULL, 'Traktamenten vid tjänsteresa', NULL, '1', '7322', 'Skattepliktiga traktamenten, Sverige'),
(1032, NULL, 'Traktamenten vid tjänsteresa', NULL, '1', '7323', 'Skattefria traktamenten, utlandet'),
(1033, NULL, 'Traktamenten vid tjänsteresa', NULL, '1', '7324', 'Skattepliktiga traktamenten, utlandet'),
(1034, '733', 'Bilersättningar', NULL, NULL, '7330', 'Bilersättningar'),
(1035, NULL, 'Bilersättningar', NULL, '1', '7331', 'Skattefria bilersättningar'),
(1036, NULL, 'Bilersättningar', NULL, '1', '7332', 'Skattepliktiga bilersättningar'),
(1037, NULL, 'Bilersättningar', NULL, NULL, '7333', 'Ersättning för trängselskatt, skattefri'),
(1038, '735', 'Ersättningar för föreskrivna arbetskläder', NULL, NULL, '7350', 'Ersättningar för föreskrivna arbetskläder'),
(1039, '737', 'Representationsersättningar', NULL, NULL, '7370', 'Representationsersättningar'),
(1040, '738', 'Kostnader för förmåner till anställda', NULL, '1', '7380', 'Kostnader för förmåner till anställda'),
(1041, NULL, 'Kostnader för förmåner till anställda', NULL, NULL, '7381', 'Kostnader för fri bostad'),
(1042, NULL, 'Kostnader för förmåner till anställda', NULL, NULL, '7382', 'Kostnader för fria eller subventionerade måltider'),
(1043, NULL, 'Kostnader för förmåner till anställda', NULL, NULL, '7383', 'Kostnader för fria resor till och från arbetsplatsen'),
(1044, NULL, 'Kostnader för förmåner till anställda', NULL, NULL, '7384', 'Kostnader för fria eller subventionerade arbetskläder'),
(1045, NULL, 'Kostnader för förmåner till anställda', NULL, '1', '7385', 'Kostnader för fri bil'),
(1046, NULL, 'Kostnader för förmåner till anställda', NULL, NULL, '7386', 'Subventionerad ränta'),
(1047, NULL, 'Kostnader för förmåner till anställda', NULL, NULL, '7387', 'Kostnader för lånedatorer'),
(1048, NULL, 'Kostnader för förmåner till anställda', NULL, NULL, '7388', 'Anställdas ersättning för erhållna förmåner'),
(1049, NULL, 'Kostnader för förmåner till anställda', NULL, NULL, '7389', 'Övriga kostnader för förmåner'),
(1050, '739', 'Övriga kostnadsersättningar och förmåner', NULL, '1', '7390', 'Övriga kostnadsersättningar och förmåner'),
(1051, NULL, 'Övriga kostnadsersättningar och förmåner', NULL, NULL, '7391', 'Kostnad för trängselskatteförmån'),
(1052, NULL, 'Övriga kostnadsersättningar och förmåner', NULL, NULL, '7392', 'Kostnad för förmån av hushållsnära tjänster'),
(1053, '74', 'Pensionskostnader', NULL, NULL, NULL, NULL),
(1054, '740', 'Pensionskostnader (gruppkonto)', NULL, NULL, '7400', 'Pensionskostnader (gruppkonto)'),
(1055, '741', 'Pensionsförsäkringspremier', NULL, '1', '7410', 'Pensionsförsäkringspremier'),
(1056, NULL, 'Pensionsförsäkringspremier', NULL, NULL, '7411', 'Premier för kollektiva pensionsförsäkringar'),
(1057, NULL, 'Pensionsförsäkringspremier', NULL, NULL, '7412', 'Premier för individuella pensionsförsäkringar'),
(1058, '742', 'Förändring av pensionsskuld', NULL, NULL, '7420', 'Förändring av pensionsskuld'),
(1059, '743', 'Avdrag för räntedel i pensionskostnad', NULL, NULL, '7430', 'Avdrag för räntedel i pensionskostnad'),
(1060, '744', 'Förändring av pensionsstiftelsekapital', NULL, NULL, '7440', 'Förändring av pensionsstiftelsekapital'),
(1061, NULL, 'Förändring av pensionsstiftelsekapital', NULL, NULL, '7441', 'Överföring av medel till pensionsstiftelse'),
(1062, NULL, 'Förändring av pensionsstiftelsekapital', NULL, NULL, '7448', 'Gottgörelse från pensionsstiftelse'),
(1063, '746', 'Pensionsutbetalningar', NULL, NULL, '7460', 'Pensionsutbetalningar'),
(1064, NULL, 'Pensionsutbetalningar', NULL, NULL, '7461', 'Pensionsutbetalningar till f.d. kollektivanställda'),
(1065, NULL, 'Pensionsutbetalningar', NULL, NULL, '7462', 'Pensionsutbetalningar till f.d. tjänstemän'),
(1066, NULL, 'Pensionsutbetalningar', NULL, NULL, '7463', 'Pensionsutbetalningar till f.d. företagsledare'),
(1067, '747', 'Förvaltnings- och kreditförsäkringsavgifter', NULL, NULL, '7470', 'Förvaltnings- och kreditförsäkringsavgifter'),
(1068, '749', 'Övriga pensionskostnader', NULL, '1', '7490', 'Övriga pensionskostnader'),
(1069, '75', 'Sociala och andra avgifter enligt lag och avtal', NULL, NULL, NULL, NULL),
(1070, '750', 'Sociala och andra avgifter enligt lag och avtal (gruppkonto)', NULL, NULL, '7500', 'Sociala och andra avgifter enligt lag och avtal (gruppkonto)'),
(1071, '751', 'Arbetsgivaravgifter 31,42 %', NULL, NULL, '7510', 'Arbetsgivaravgifter 31,42 %'),
(1072, NULL, 'Arbetsgivaravgifter 31,42 %', NULL, '1', '7511', 'Arbetsgivaravgifter för löner och ersättningar'),
(1073, NULL, 'Arbetsgivaravgifter 31,42 %', NULL, '1', '7512', 'Arbetsgivaravgifter för förmånsvärden'),
(1074, NULL, 'Arbetsgivaravgifter 31,42 %', NULL, NULL, '7515', 'Arbetsgivaravgifter på skattepliktiga kostnadsersättningar'),
(1075, NULL, 'Arbetsgivaravgifter 31,42 %', NULL, NULL, '7516', 'Arbetsgivaravgifter på arvoden'),
(1076, NULL, 'Arbetsgivaravgifter 31,42 %', NULL, NULL, '7518', 'Arbetsgivaravgifter på bruttolöneavdrag m.m.'),
(1077, NULL, 'Arbetsgivaravgifter 31,42 %', NULL, '1', '7519', 'Arbetsgivaravgifter för semester- och löneskulder'),
(1078, '753', 'Särskild löneskatt', NULL, '1', '7530', 'Särskild löneskatt'),
(1079, NULL, 'Särskild löneskatt', NULL, NULL, '7531', 'Särskild löneskatt för vissa försäkringsersättningar m.m.'),
(1080, NULL, 'Särskild löneskatt', NULL, NULL, '7532', 'Särskild löneskatt pensionskostnader, deklarationspost'),
(1081, NULL, 'Särskild löneskatt', NULL, NULL, '7533', 'Särskild löneskatt för pensionskostnader'),
(1082, '755', 'Avkastningsskatt på pensionsmedel', NULL, '1', '7550', 'Avkastningsskatt på pensionsmedel'),
(1083, NULL, 'Avkastningsskatt på pensionsmedel', NULL, NULL, '7551', 'Avkastningsskatt 15 % försäkringsföretag m.fl. samt avsatt till pensioner'),
(1084, NULL, 'Avkastningsskatt på pensionsmedel', NULL, NULL, '7552', 'Avkastningsskatt 15 % utländska pensionsförsäkringar'),
(1085, NULL, 'Avkastningsskatt på pensionsmedel', NULL, NULL, '7553', 'Avkastningsskatt 30 % utländska försäkringsföretag m.fl.'),
(1086, NULL, 'Avkastningsskatt på pensionsmedel', NULL, NULL, '7554', 'Avkastningsskatt 30 % utländska kapitalförsäkringar'),
(1087, '757', 'Premier för arbetsmarknadsförsäkringar', NULL, '1', '7570', 'Premier för arbetsmarknadsförsäkringar'),
(1088, NULL, 'Premier för arbetsmarknadsförsäkringar', NULL, NULL, '7571', 'Arbetsmarknadsförsäkringar'),
(1089, NULL, 'Premier för arbetsmarknadsförsäkringar', NULL, NULL, '7572', 'Arbetsmarknadsförsäkringar pensionsförsäkringspremier, deklarationspost'),
(1090, '758', 'Gruppförsäkringspremier', NULL, '1', '7580', 'Gruppförsäkringspremier'),
(1091, NULL, 'Gruppförsäkringspremier', NULL, NULL, '7581', 'Grupplivförsäkringspremier'),
(1092, NULL, 'Gruppförsäkringspremier', NULL, NULL, '7582', 'Gruppsjukförsäkringspremier'),
(1093, NULL, 'Gruppförsäkringspremier', NULL, NULL, '7583', 'Gruppolycksfallsförsäkringspremier'),
(1094, NULL, 'Gruppförsäkringspremier', NULL, NULL, '7589', 'Övriga gruppförsäkringspremier'),
(1095, '759', 'Övriga sociala och andra avgifter enligt lag och avtal', NULL, '1', '7590', 'Övriga sociala och andra avgifter enligt lag och avtal'),
(1096, '76', 'Övriga personalkostnader', NULL, NULL, NULL, NULL),
(1097, '760', 'Övriga personalkostnader (gruppkonto)', NULL, '1', '7600', 'Övriga personalkostnader (gruppkonto)'),
(1098, '761', 'Utbildning', NULL, '1', '7610', 'Utbildning'),
(1099, '762', 'Sjuk- och hälsovård', NULL, NULL, '7620', 'Sjuk- och hälsovård'),
(1100, NULL, 'Sjuk- och hälsovård', NULL, '1', '7621', 'Sjuk- och hälsovård, avdragsgill'),
(1101, NULL, 'Sjuk- och hälsovård', NULL, '1', '7622', 'Sjuk- och hälsovård, ej avdragsgill'),
(1102, NULL, 'Sjuk- och hälsovård', NULL, NULL, '7623', 'Sjukvårdsförsäkring, ej avdragsgill'),
(1103, '763', 'Personalrepresentation', NULL, NULL, '7630', 'Personalrepresentation'),
(1104, NULL, 'Personalrepresentation', NULL, '1', '7631', 'Personalrepresentation, avdragsgill'),
(1105, NULL, 'Personalrepresentation', NULL, '1', '7632', 'Personalrepresentation, ej avdragsgill'),
(1106, '765', 'Sjuklöneförsäkring', NULL, NULL, '7650', 'Sjuklöneförsäkring'),
(1107, '767', 'Förändring av personalstiftelsekapital', NULL, NULL, '7670', 'Förändring av personalstiftelsekapital'),
(1108, NULL, 'Förändring av personalstiftelsekapital', NULL, NULL, '7671', 'Avsättning till personalstiftelse'),
(1109, NULL, 'Förändring av personalstiftelsekapital', NULL, NULL, '7678', 'Gottgörelse från personalstiftelse'),
(1110, '769', 'Övriga personalkostnader', NULL, NULL, '7690', 'Övriga personalkostnader'),
(1111, NULL, 'Övriga personalkostnader', NULL, NULL, '7691', 'Personalrekrytering'),
(1112, NULL, 'Övriga personalkostnader', NULL, NULL, '7692', 'Begravningshjälp'),
(1113, NULL, 'Övriga personalkostnader', NULL, NULL, '7693', 'Fritidsverksamhet'),
(1114, NULL, 'Övriga personalkostnader', NULL, NULL, '7699', 'Övriga personalkostnader'),
(1115, '77', 'Nedskrivningar och återföring av nedskrivningar', NULL, NULL, NULL, NULL),
(1116, '771', 'Nedskrivningar av immateriella anläggningstillgångar', NULL, NULL, '7710', 'Nedskrivningar av immateriella anläggningstillgångar'),
(1117, '772', 'Nedskrivningar av byggnader och mark', NULL, '1', '7720', 'Nedskrivningar av byggnader och mark'),
(1118, '773', 'Nedskrivningar av maskiner och inventarier', NULL, '1', '7730', 'Nedskrivningar av maskiner och inventarier'),
(1119, '774', 'Nedskrivningar av vissa omsättningstillgångar', NULL, NULL, '7740', 'Nedskrivningar av vissa omsättningstillgångar'),
(1120, '776', 'Återföring av nedskrivningar av immateriella anläggningstillgångar', NULL, NULL, '7760', 'Återföring av nedskrivningar av immateriella anläggningstillgångar'),
(1121, '777', 'Återföring av nedskrivningar av byggnader och mark', NULL, NULL, '7770', 'Återföring av nedskrivningar av byggnader och mark'),
(1122, '778', 'Återföring av nedskrivningar av maskiner och inventarier', NULL, NULL, '7780', 'Återföring av nedskrivningar av maskiner och inventarier'),
(1123, '779', 'Återföring av nedskrivningar av vissa omsättningstillgångar', NULL, NULL, '7790', 'Återföring av nedskrivningar av vissa omsättningstillgångar'),
(1124, '78', 'Avskrivningar enligt plan', NULL, NULL, NULL, NULL),
(1125, '781', 'Avskrivningar på immateriella anläggningstillgångar', NULL, '1', '7810', 'Avskrivningar på immateriella anläggningstillgångar'),
(1126, NULL, 'Avskrivningar på immateriella anläggningstillgångar', NULL, NULL, '7811', 'Avskrivningar på balanserade utgifter'),
(1127, NULL, 'Avskrivningar på immateriella anläggningstillgångar', NULL, NULL, '7812', 'Avskrivningar på koncessioner m.m.'),
(1128, NULL, 'Avskrivningar på immateriella anläggningstillgångar', NULL, NULL, '7813', 'Avskrivningar på patent'),
(1129, NULL, 'Avskrivningar på immateriella anläggningstillgångar', NULL, NULL, '7814', 'Avskrivningar på licenser'),
(1130, NULL, 'Avskrivningar på immateriella anläggningstillgångar', NULL, NULL, '7815', 'Avskrivningar på varumärken'),
(1131, NULL, 'Avskrivningar på immateriella anläggningstillgångar', NULL, NULL, '7816', 'Avskrivningar på hyresrätter'),
(1132, NULL, 'Avskrivningar på immateriella anläggningstillgångar', NULL, NULL, '7817', 'Avskrivningar på goodwill'),
(1133, NULL, 'Avskrivningar på immateriella anläggningstillgångar', NULL, NULL, '7819', 'Avskrivningar på övriga immateriella anläggningstillgångar'),
(1134, '782', 'Avskrivningar på byggnader och markanläggningar', NULL, '1', '7820', 'Avskrivningar på byggnader och markanläggningar'),
(1135, NULL, 'Avskrivningar på byggnader och markanläggningar', NULL, NULL, '7821', 'Avskrivningar på byggnader'),
(1136, NULL, 'Avskrivningar på byggnader och markanläggningar', NULL, NULL, '7824', 'Avskrivningar på markanläggningar'),
(1137, NULL, 'Avskrivningar på byggnader och markanläggningar', NULL, NULL, '7829', 'Avskrivningar på övriga byggnader'),
(1138, '783', 'Avskrivningar på maskiner och inventarier', NULL, '1', '7830', 'Avskrivningar på maskiner och inventarier'),
(1139, NULL, 'Avskrivningar på maskiner och inventarier', NULL, NULL, '7831', 'Avskrivningar på maskiner och andra tekniska anläggningar'),
(1140, NULL, 'Avskrivningar på maskiner och inventarier', NULL, NULL, '7832', 'Avskrivningar på inventarier och verktyg'),
(1141, NULL, 'Avskrivningar på maskiner och inventarier', NULL, NULL, '7833', 'Avskrivningar på installationer'),
(1142, NULL, 'Avskrivningar på maskiner och inventarier', NULL, NULL, '7834', 'Avskrivningar på bilar och andra transportmedel'),
(1143, NULL, 'Avskrivningar på maskiner och inventarier', NULL, NULL, '7835', 'Avskrivningar på datorer'),
(1144, NULL, 'Avskrivningar på maskiner och inventarier', NULL, NULL, '7836', 'Avskrivningar på leasade tillgångar'),
(1145, NULL, 'Avskrivningar på maskiner och inventarier', NULL, NULL, '7839', 'Avskrivningar på övriga maskiner och inventarier'),
(1146, '784', 'Avskrivningar på förbättringsutgifter på annans fastighet', NULL, NULL, '7840', 'Avskrivningar på förbättringsutgifter på annans fastighet'),
(1147, '79', 'Övriga rörelsekostnader', NULL, NULL, NULL, NULL),
(1148, '794', 'Orealiserade positiva/negativa värdeförändringar på säkringsinstrument', 1, NULL, '7940', 'Orealiserade positiva/negativa värdeförändringar på säkringsinstrument'),
(1149, '796', 'Valutakursförluster på fordringar och skulder av rörelsekaraktär', NULL, NULL, '7960', 'Valutakursförluster på fordringar och skulder av rörelsekaraktär'),
(1150, '797', 'Förlust vid avyttring av immateriella och materiella anläggningstillgångar', NULL, '1', '7970', 'Förlust vid avyttring av immateriella och materiella anläggningstillgångar'),
(1151, NULL, 'Förlust vid avyttring av immateriella och materiella anläggningstillgångar', NULL, NULL, '7971', 'Förlust vid avyttring av immateriella anläggningstillgångar'),
(1152, NULL, 'Förlust vid avyttring av immateriella och materiella anläggningstillgångar', NULL, NULL, '7972', 'Förlust vid avyttring av byggnader och mark'),
(1153, NULL, 'Förlust vid avyttring av immateriella och materiella anläggningstillgångar', NULL, NULL, '7973', 'Förlust vid avyttring av maskiner och inventarier'),
(1154, '799', 'Övriga rörelsekostnader', NULL, '1', '7990', 'Övriga rörelsekostnader'),
(1155, '8', 'Finansiella och andra inkomster/ intäkter och utgifter/kostnader', NULL, NULL, NULL, NULL),
(1156, '80', 'Resultat från andelar i koncernföretag', NULL, NULL, NULL, NULL),
(1157, '801', 'Utdelning på andelar i koncernföretag', NULL, NULL, '8010', 'Utdelning på andelar i koncernföretag'),
(1158, NULL, 'Utdelning på andelar i koncernföretag', NULL, NULL, '8012', 'Utdelning på andelar i dotterföretag'),
(1159, NULL, 'Utdelning på andelar i koncernföretag', NULL, NULL, '8016', 'Emissionsinsats, koncernföretag'),
(1160, '802', 'Resultat vid försäljning av andelar i koncernföretag', NULL, NULL, '8020', 'Resultat vid försäljning av andelar i koncernföretag'),
(1161, NULL, 'Resultat vid försäljning av andelar i koncernföretag', NULL, NULL, '8022', 'Resultat vid försäljning av andelar i dotterföretag'),
(1162, '803', 'Resultatandelar från handelsbolag (dotterföretag)', NULL, NULL, '8030', 'Resultatandelar från handelsbolag (dotterföretag)'),
(1163, '807', 'Nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', NULL, NULL, '8070', 'Nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag'),
(1164, NULL, 'Nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', NULL, NULL, '8072', 'Nedskrivningar av andelar i dotterföretag'),
(1165, NULL, 'Nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', NULL, NULL, '8076', 'Nedskrivningar av långfristiga fordringar hos moderföretag'),
(1166, NULL, 'Nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', NULL, NULL, '8077', 'Nedskrivningar av långfristiga fordringar hos dotterföretag'),
(1167, '808', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', NULL, NULL, '8080', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag'),
(1168, NULL, 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', NULL, NULL, '8082', 'Återföringar av nedskrivningar av andelar i dotterföretag'),
(1169, NULL, 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', NULL, NULL, '8086', 'Återföringar av nedskrivningar av långfristiga fordringar hos moderföretag'),
(1170, NULL, 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', NULL, NULL, '8087', 'Återföringar av nedskrivningar av långfristiga fordringar hos dotterföretag'),
(1171, '81', 'Resultat från andelar i intresseföretag', NULL, NULL, NULL, NULL),
(1172, '811', 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8110', 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(1173, NULL, 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8111', 'Utdelningar på andelar i intresseföretag'),
(1174, NULL, 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8112', 'Utdelningar på andelar i gemensamt styrda företag'),
(1175, NULL, 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8113', 'Utdelningar på andelar i övriga företag som det finns ett ägarintresse i'),
(1176, NULL, 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8116', 'Emissionsinsats, intresseföretag'),
(1177, NULL, 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8117', 'Emissionsinsats, gemensamt styrda företag'),
(1178, NULL, 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8118', 'Emissionsinsats, övriga företag som det finns ett ägarintresse i'),
(1179, '812', 'Resultat vid försäljning av andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8120', 'Resultat vid försäljning av andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(1180, NULL, 'Resultat vid försäljning av andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8121', 'Resultat vid försäljning av andelar i intresseföretag'),
(1181, NULL, 'Resultat vid försäljning av andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8122', 'Resultat vid försäljning av andelar i gemensamt styrda företag'),
(1182, NULL, 'Resultat vid försäljning av andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8123', 'Resultat vid försäljning av andelar i övriga företag som det finns ett ägarintresse i'),
(1183, '813', 'Resultatandelar från handelsbolag (intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i)', NULL, NULL, '8130', 'Resultatandelar från handelsbolag (intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i)'),
(1184, NULL, 'Resultatandelar från handelsbolag (intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i)', NULL, NULL, '8131', 'Resultatandelar från handelsbolag (intresseföretag)'),
(1185, NULL, 'Resultatandelar från handelsbolag (intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i)', NULL, NULL, '8132', 'Resultatandelar från handelsbolag (gemensamt styrda företag)'),
(1186, NULL, 'Resultatandelar från handelsbolag (intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i)', NULL, NULL, '8133', 'Resultatandelar från handelsbolag (övriga företag som det finns ett ägarintresse i)'),
(1187, '817', 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8170', 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(1188, NULL, 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8171', 'Nedskrivningar av andelar i intresseföretag'),
(1189, NULL, 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8172', 'Nedskrivningar av långfristiga fordringar hos intresseföretag'),
(1190, NULL, 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8173', 'Nedskrivningar av andelar i gemensamt styrda företag'),
(1191, NULL, 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8174', 'Nedskrivningar av långfristiga fordringar hos gemensamt styrda företag'),
(1192, NULL, 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8176', 'Nedskrivningar av andelar i övriga företag som det finns ett ägarintresse i'),
(1193, NULL, 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', NULL, NULL, '8177', 'Nedskrivningar av långfristiga fordringar hos övriga företag som det finns ett ägarintresse i'),
(1194, '818', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag', NULL, NULL, '8180', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag'),
(1195, NULL, 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag', NULL, NULL, '8181', 'Återföringar av nedskrivningar av andelar i intresseföretag'),
(1196, NULL, 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag', NULL, NULL, '8182', 'Återföringar av nedskrivningar av långfristiga fordringar hos intresseföretag'),
(1197, NULL, 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag', NULL, NULL, '8183', 'Återföringar av nedskrivningar av andelar i gemensamt styrda företag'),
(1198, NULL, 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag', NULL, NULL, '8184', 'Återföringar av nedskrivningar av långfristiga fordringar hos gemensamt styrda företag'),
(1199, NULL, 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag', NULL, NULL, '8186', 'Återföringar av nedskrivningar av andelar i övriga företag som det finns ett ägarintresse i'),
(1200, NULL, 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag', NULL, NULL, '8187', 'Återföringar av nedskrivningar av långfristiga fordringar hos övriga företag som det finns ett ägarintresse i'),
(1201, '82', 'Resultat från övriga värdepapper och långfristiga fordringar (anläggningstillgångar)', NULL, NULL, NULL, NULL),
(1202, '821', 'Utdelningar på andelar i andra företag', NULL, '1', '8210', 'Utdelningar på andelar i andra företag'),
(1203, NULL, 'Utdelningar på andelar i andra företag', NULL, NULL, '8212', 'Utdelningar, övriga företag'),
(1204, NULL, 'Utdelningar på andelar i andra företag', NULL, NULL, '8216', 'Insatsemissioner, övriga företag'),
(1205, '822', 'Resultat vid försäljning av värdepapper i och långfristiga fordringar hos andra företag', NULL, '1', '8220', 'Resultat vid försäljning av värdepapper i och långfristiga fordringar hos andra företag'),
(1206, NULL, 'Resultat vid försäljning av värdepapper i och långfristiga fordringar hos andra företag', NULL, NULL, '8221', 'Resultat vid försäljning av andelar i andra företag'),
(1207, NULL, 'Resultat vid försäljning av värdepapper i och långfristiga fordringar hos andra företag', NULL, NULL, '8222', 'Resultat vid försäljning av långfristiga fordringar hos andra företag'),
(1208, NULL, 'Resultat vid försäljning av värdepapper i och långfristiga fordringar hos andra företag', NULL, NULL, '8223', 'Resultat vid försäljning av derivat (långfristiga värdepappersinnehav)'),
(1209, '823', 'Valutakursdifferenser på långfristiga fordringar', NULL, NULL, '8230', 'Valutakursdifferenser på långfristiga fordringar'),
(1210, NULL, 'Valutakursdifferenser på långfristiga fordringar', NULL, NULL, '8231', 'Valutakursvinster på långfristiga fordringar'),
(1211, NULL, 'Valutakursdifferenser på långfristiga fordringar', NULL, NULL, '8236', 'Valutakursförluster på långfristiga fordringar'),
(1212, '824', 'Resultatandelar från handelsbolag (andra företag)', NULL, NULL, '8240', 'Resultatandelar från handelsbolag (andra företag)'),
(1213, '825', 'Ränteintäkter från långfristiga fordringar hos och värdepapper i andra företag', NULL, '1', '8250', 'Ränteintäkter från långfristiga fordringar hos och värdepapper i andra företag'),
(1214, NULL, 'Ränteintäkter från långfristiga fordringar hos och värdepapper i andra företag', NULL, NULL, '8251', 'Ränteintäkter från långfristiga fordringar'),
(1215, NULL, 'Ränteintäkter från långfristiga fordringar hos och värdepapper i andra företag', NULL, NULL, '8252', 'Ränteintäkter från övriga värdepapper'),
(1216, NULL, 'Ränteintäkter från långfristiga fordringar hos och värdepapper i andra företag', NULL, NULL, '8254', 'Skattefria ränteintäkter, långfristiga tillgångar'),
(1217, NULL, 'Ränteintäkter från långfristiga fordringar hos och värdepapper i andra företag', NULL, NULL, '8255', 'Avkastningsskatt kapitalplacering'),
(1218, '826', 'Ränteintäkter från långfristiga fordringar hos koncernföretag', NULL, NULL, '8260', 'Ränteintäkter från långfristiga fordringar hos koncernföretag'),
(1219, NULL, 'Ränteintäkter från långfristiga fordringar hos koncernföretag', NULL, NULL, '8261', 'Ränteintäkter från långfristiga fordringar hos moderföretag'),
(1220, NULL, 'Ränteintäkter från långfristiga fordringar hos koncernföretag', NULL, NULL, '8262', 'Ränteintäkter från långfristiga fordringar hos dotterföretag'),
(1221, NULL, 'Ränteintäkter från långfristiga fordringar hos koncernföretag', NULL, NULL, '8263', 'Ränteintäkter från långfristiga fordringar hos andra koncernföretag'),
(1222, '827', 'Nedskrivningar av innehav av andelar i och långfristiga fordringar hos andra företag', NULL, '1', '8270', 'Nedskrivningar av innehav av andelar i och långfristiga fordringar hos andra företag'),
(1223, NULL, 'Nedskrivningar av innehav av andelar i och långfristiga fordringar hos andra företag', NULL, NULL, '8271', 'Nedskrivningar av andelar i andra företag'),
(1224, NULL, 'Nedskrivningar av innehav av andelar i och långfristiga fordringar hos andra företag', NULL, NULL, '8272', 'Nedskrivningar av långfristiga fordringar hos andra företag'),
(1225, NULL, 'Nedskrivningar av innehav av andelar i och långfristiga fordringar hos andra företag', NULL, NULL, '8273', 'Nedskrivningar av övriga värdepapper hos andra företag'),
(1226, '828', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos andra företag', NULL, NULL, '8280', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos andra företag'),
(1227, NULL, 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos andra företag', NULL, NULL, '8281', 'Återföringar av nedskrivningar av andelar i andra företag'),
(1228, NULL, 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos andra företag', NULL, NULL, '8282', 'Återföringar av nedskrivningar av långfristiga fordringar hos andra företag'),
(1229, NULL, 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos andra företag', NULL, NULL, '8283', 'Återföringar av nedskrivningar av övriga värdepapper i andra företag'),
(1230, '829', 'Värdering till verkligt värde, anläggningstillgångar', 1, NULL, '8290', 'Värdering till verkligt värde, anläggningstillgångar'),
(1231, NULL, 'Värdering till verkligt värde, anläggningstillgångar', 1, NULL, '8291', 'Orealiserade värdeförändringar på anläggningstillgångar'),
(1232, NULL, 'Värdering till verkligt värde, anläggningstillgångar', 1, NULL, '8295', 'Orealiserade värdeförändringar på derivatinstrument'),
(1233, '83', 'Övriga ränteintäkter och liknande resultatposter', NULL, NULL, NULL, NULL),
(1234, '831', 'Ränteintäkter från omsättningstillgångar', NULL, '1', '8310', 'Ränteintäkter från omsättningstillgångar'),
(1235, NULL, 'Ränteintäkter från omsättningstillgångar', NULL, NULL, '8311', 'Ränteintäkter från bank'),
(1236, NULL, 'Ränteintäkter från omsättningstillgångar', NULL, NULL, '8312', 'Ränteintäkter från kortfristiga placeringar'),
(1237, NULL, 'Ränteintäkter från omsättningstillgångar', NULL, NULL, '8313', 'Ränteintäkter från kortfristiga fordringar'),
(1238, NULL, 'Ränteintäkter från omsättningstillgångar', NULL, '1', '8314', 'Skattefria ränteintäkter'),
(1239, NULL, 'Ränteintäkter från omsättningstillgångar', NULL, NULL, '8317', 'Ränteintäkter för dold räntekompensation'),
(1240, NULL, 'Ränteintäkter från omsättningstillgångar', NULL, NULL, '8319', 'Övriga ränteintäkter från omsättningstillgångar'),
(1241, '832', 'Värdering till verkligt värde, omsättningstillgångar', 1, NULL, '8320', 'Värdering till verkligt värde, omsättningstillgångar'),
(1242, NULL, 'Värdering till verkligt värde, omsättningstillgångar', 1, NULL, '8321', 'Orealiserade värdeförändringar på omsättningstillgångar'),
(1243, NULL, 'Värdering till verkligt värde, omsättningstillgångar', 1, NULL, '8325', 'Orealiserade värdeförändringar på derivatinstrument (oms.-tillg.)'),
(1244, '833', 'Valutakursdifferenser på kortfristiga fordringar och placeringar', NULL, '1', '8330', 'Valutakursdifferenser på kortfristiga fordringar och placeringar'),
(1245, NULL, 'Valutakursdifferenser på kortfristiga fordringar och placeringar', NULL, NULL, '8331', 'Valutakursvinster på kortfristiga fordringar och placeringar'),
(1246, NULL, 'Valutakursdifferenser på kortfristiga fordringar och placeringar', NULL, NULL, '8336', 'Valutakursförluster på kortfristiga fordringar och placeringar'),
(1247, '834', 'Utdelningar på kortfristiga placeringar', NULL, '1', '8340', 'Utdelningar på kortfristiga placeringar'),
(1248, '835', 'Resultat vid försäljning av kortfristiga placeringar', NULL, '1', '8350', 'Resultat vid försäljning av kortfristiga placeringar'),
(1249, '836', 'Övriga ränteintäkter från koncernföretag', NULL, NULL, '8360', 'Övriga ränteintäkter från koncernföretag'),
(1250, NULL, 'Övriga ränteintäkter från koncernföretag', NULL, NULL, '8361', 'Övriga ränteintäkter från moderföretag'),
(1251, NULL, 'Övriga ränteintäkter från koncernföretag', NULL, NULL, '8362', 'Övriga ränteintäkter från dotterföretag'),
(1252, NULL, 'Övriga ränteintäkter från koncernföretag', NULL, NULL, '8363', 'Övriga ränteintäkter från andra koncernföretag'),
(1253, '837', 'Nedskrivningar av kortfristiga placeringar', NULL, NULL, '8370', 'Nedskrivningar av kortfristiga placeringar'),
(1254, '838', 'Återföringar av nedskrivningar av kortfristiga placeringar', NULL, NULL, '8380', 'Återföringar av nedskrivningar av kortfristiga placeringar'),
(1255, '839', 'Övriga finansiella intäkter', NULL, '1', '8390', 'Övriga finansiella intäkter'),
(1256, '84', 'Räntekostnader och liknande resultatposter', NULL, NULL, NULL, NULL),
(1257, '840', 'Räntekostnader (gruppkonto)', NULL, NULL, '8400', 'Räntekostnader (gruppkonto)'),
(1258, '841', 'Räntekostnader för långfristiga skulder', NULL, '1', '8410', 'Räntekostnader för långfristiga skulder'),
(1259, NULL, 'Räntekostnader för långfristiga skulder', NULL, NULL, '8411', 'Räntekostnader för obligations-, förlags- och konvertibla lån'),
(1260, NULL, 'Räntekostnader för långfristiga skulder', NULL, NULL, '8412', 'Räntedel i årets pensionskostnad'),
(1261, NULL, 'Räntekostnader för långfristiga skulder', NULL, NULL, '8413', 'Räntekostnader för checkräkningskredit'),
(1262, NULL, 'Räntekostnader för långfristiga skulder', NULL, NULL, '8415', 'Räntekostnader för andra skulder till kreditinstitut'),
(1263, NULL, 'Räntekostnader för långfristiga skulder', 1, NULL, '8417', 'Räntekostnader för dold räntekompensation m.m.'),
(1264, NULL, 'Räntekostnader för långfristiga skulder', NULL, NULL, '8418', 'Avdragspost för räntesubventioner'),
(1265, NULL, 'Räntekostnader för långfristiga skulder', NULL, NULL, '8419', 'Övriga räntekostnader för långfristiga skulder'),
(1266, '842', 'Räntekostnader för kortfristiga skulder', NULL, '1', '8420', 'Räntekostnader för kortfristiga skulder'),
(1267, NULL, 'Räntekostnader för kortfristiga skulder', NULL, NULL, '8421', 'Räntekostnader till kreditinstitut'),
(1268, NULL, 'Räntekostnader för kortfristiga skulder', NULL, '1', '8422', 'Dröjsmålsräntor för leverantörsskulder'),
(1269, NULL, 'Räntekostnader för kortfristiga skulder', NULL, '1', '8423', 'Räntekostnader för skatter och avgifter'),
(1270, NULL, 'Räntekostnader för kortfristiga skulder', NULL, NULL, '8424', 'Räntekostnader byggnadskreditiv'),
(1271, NULL, 'Räntekostnader för kortfristiga skulder', NULL, NULL, '8429', 'Övriga räntekostnader för kortfristiga skulder'),
(1272, '843', 'Valutakursdifferenser på skulder', NULL, '1', '8430', 'Valutakursdifferenser på skulder'),
(1273, NULL, 'Valutakursdifferenser på skulder', NULL, NULL, '8431', 'Valutakursvinster på skulder'),
(1274, NULL, 'Valutakursdifferenser på skulder', NULL, NULL, '8436', 'Valutakursförluster på skulder'),
(1275, '844', 'Erhållna räntebidrag', NULL, NULL, '8440', 'Erhållna räntebidrag'),
(1276, '845', 'Orealiserade värdeförändringar på skulder', 1, NULL, '8450', 'Orealiserade värdeförändringar på skulder'),
(1277, NULL, 'Orealiserade värdeförändringar på skulder', 1, NULL, '8451', 'Orealiserade värdeförändringar på skulder'),
(1278, NULL, 'Orealiserade värdeförändringar på skulder', 1, NULL, '8455', 'Orealiserade värdeförändringar på säkringsinstrument'),
(1279, '846', 'Räntekostnader till koncernföretag', NULL, NULL, '8460', 'Räntekostnader till koncernföretag'),
(1280, NULL, 'Räntekostnader till koncernföretag', NULL, NULL, '8461', 'Räntekostnader till moderföretag'),
(1281, NULL, 'Räntekostnader till koncernföretag', NULL, NULL, '8462', 'Räntekostnader till dotterföretag'),
(1282, NULL, 'Räntekostnader till koncernföretag', NULL, NULL, '8463', 'Räntekostnader till andra koncernföretag'),
(1283, '848', 'Aktiverade ränteutgifter', 1, NULL, '8480', 'Aktiverade ränteutgifter'),
(1284, '849', 'Övriga skuldrelaterade poster', NULL, NULL, '8490', 'Övriga skuldrelaterade poster'),
(1285, NULL, 'Övriga skuldrelaterade poster', NULL, NULL, '8491', 'Erhållet ackord på skulder till kreditinstitut m.m.'),
(1286, '85', '(Fri kontogrupp)', NULL, NULL, NULL, NULL),
(1287, '86', '(Fri kontogrupp)', NULL, NULL, NULL, NULL),
(1288, '87', '(Fri kontogrupp)', NULL, NULL, NULL, NULL),
(1289, '88', 'Bokslutsdispositioner', NULL, NULL, NULL, NULL),
(1290, '881', 'Förändring av periodiseringsfond', NULL, NULL, '8810', 'Förändring av periodiseringsfond'),
(1291, NULL, NULL, NULL, '1', '8811', 'Avsättning till periodiseringsfond'),
(1292, NULL, NULL, NULL, '1', '8819', 'Återföring från periodiseringsfond'),
(1293, '882', 'Mottagna koncernbidrag', NULL, NULL, '8820', 'Mottagna koncernbidrag'),
(1294, '883', 'Lämnade koncernbidrag', NULL, NULL, '8830', 'Lämnade koncernbidrag'),
(1295, '884', 'Lämnade gottgörelser', NULL, NULL, '8840', 'Lämnade gottgörelser'),
(1296, '885', 'Förändring av överavskrivningar', NULL, '1', '8850', 'Förändring av överavskrivningar'),
(1297, NULL, 'Förändring av överavskrivningar', NULL, NULL, '8851', 'Förändring av överavskrivningar, immateriella anläggningstillgångar'),
(1298, NULL, 'Förändring av överavskrivningar', NULL, NULL, '8852', 'Förändring av överavskrivningar, byggnader och markanläggningar'),
(1299, NULL, 'Förändring av överavskrivningar', NULL, NULL, '8853', 'Förändring av överavskrivningar, maskiner och inventarier'),
(1300, '886', 'Förändring av ersättningsfond', NULL, NULL, '8860', 'Förändring av ersättningsfond'),
(1301, NULL, 'Förändring av ersättningsfond', NULL, NULL, '8861', 'Avsättning till ersättningsfond för inventarier'),
(1302, NULL, 'Förändring av ersättningsfond', NULL, NULL, '8862', 'Avsättning till ersättningsfond för byggnader och markanläggningar'),
(1303, NULL, 'Förändring av ersättningsfond', NULL, NULL, '8864', 'Avsättning till ersättningsfond för djurlager i jordbruk och renskötsel'),
(1304, NULL, 'Förändring av ersättningsfond', NULL, NULL, '8865', 'Ianspråktagande av ersättningsfond för avskrivningar'),
(1305, NULL, 'Förändring av ersättningsfond', NULL, NULL, '8866', 'Ianspråktagande av ersättningsfond för annat än avskrivningar'),
(1306, NULL, 'Förändring av ersättningsfond', NULL, NULL, '8869', 'Återföring från ersättningsfond'),
(1307, '889', 'Övriga bokslutsdispositioner', NULL, NULL, '8890', 'Övriga bokslutsdispositioner'),
(1308, NULL, 'Övriga bokslutsdispositioner', NULL, NULL, '8892', 'Nedskrivningar av konsolideringskaraktär av anläggningstillgångar'),
(1309, NULL, 'Övriga bokslutsdispositioner', NULL, NULL, '8896', 'Förändring av lagerreserv'),
(1310, NULL, 'Övriga bokslutsdispositioner', NULL, NULL, '8899', 'Övriga bokslutsdispositioner'),
(1311, '89', 'Skatter och årets resultat', NULL, NULL, NULL, NULL),
(1312, '891', 'Skatt på grund av ändrad beskattning', NULL, '1', '8910', 'Skatt som belastar årets resultat'),
(1313, '892', 'Skatt som belastar årets resultat', NULL, NULL, '8920', 'Skatt på grund av ändrad beskattning'),
(1314, '893', 'Restituerad skatt', NULL, NULL, '8930', 'Restituerad skatt'),
(1315, '894', 'Uppskjuten skatt', 1, NULL, '8940', 'Uppskjuten skatt'),
(1316, '898', 'Övriga skatter', NULL, NULL, '8980', 'Övriga skatter'),
(1317, '899', 'Resultat', NULL, '1', '8990', 'Resultat'),
(1318, NULL, NULL, NULL, '1', '8999', 'Årets resultat');

-- --------------------------------------------------------

--
-- Tabellstruktur `companies`
--

CREATE TABLE `companies` (
  `id` int NOT NULL,
  `name` varchar(234) NOT NULL,
  `orgnr` varchar(22) NOT NULL,
  `address` varchar(222) DEFAULT NULL,
  `address2` varchar(222) DEFAULT NULL,
  `zip` varchar(123) DEFAULT NULL,
  `city` varchar(234) DEFAULT NULL,
  `country` varchar(234) DEFAULT NULL,
  `phone` varchar(234) DEFAULT NULL,
  `www` varchar(234) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `companies`
--

INSERT INTO `companies` (`id`, `name`, `orgnr`, `address`, `address2`, `zip`, `city`, `country`, `phone`, `www`, `created_at`, `updated_at`) VALUES
(5, 'Kjell & Co Kungsholmen Sthlm', '556400-5378', 'Kronobergsgatan 33', NULL, '112 33', 'Stockholm', 'Sweden', '08-50 10 18 20', NULL, '2025-10-02 10:48:43', '2025-10-02 11:50:04'),
(6, 'BAUHAUS', '30308472', NULL, NULL, '16867', 'Bromma', 'Sweden', NULL, NULL, '2025-10-02 11:32:24', '2025-10-02 14:30:04'),
(7, 'HORNBACH', '556613-4853', 'Madenvägen 17', NULL, '174 55', 'Sundbyberg', 'Sweden', '08-799 50 00', 'www.hornbach.se', '2025-10-02 11:33:36', '2025-10-02 14:30:05');

-- --------------------------------------------------------

--
-- Tabellstruktur `creditcard_invoices_main`
--

CREATE TABLE `creditcard_invoices_main` (
  `id` bigint UNSIGNED NOT NULL,
  `invoice_number` varchar(50) NOT NULL,
  `invoice_print_time` datetime DEFAULT NULL,
  `card_type` varchar(50) DEFAULT NULL,
  `card_name` varchar(100) DEFAULT NULL,
  `card_number_masked` varchar(32) DEFAULT NULL,
  `card_holder` varchar(100) DEFAULT NULL,
  `cost_center` varchar(100) DEFAULT NULL,
  `customer_name` varchar(150) DEFAULT NULL,
  `co` varchar(150) DEFAULT NULL,
  `address` text,
  `bank_name` varchar(100) DEFAULT NULL,
  `bank_org_no` varchar(50) DEFAULT NULL,
  `bank_vat_no` varchar(50) DEFAULT NULL,
  `bank_fi_no` varchar(50) DEFAULT NULL,
  `invoice_date` date DEFAULT NULL,
  `customer_number` varchar(50) DEFAULT NULL,
  `invoice_number_long` varchar(100) DEFAULT NULL,
  `due_date` date DEFAULT NULL,
  `invoice_total` decimal(13,2) DEFAULT NULL,
  `payment_plusgiro` varchar(30) DEFAULT NULL,
  `payment_bankgiro` varchar(30) DEFAULT NULL,
  `payment_iban` varchar(34) DEFAULT NULL,
  `payment_bic` varchar(11) DEFAULT NULL,
  `payment_ocr` varchar(50) DEFAULT NULL,
  `payment_due` date DEFAULT NULL,
  `card_total` decimal(13,2) DEFAULT NULL,
  `sum` decimal(13,2) DEFAULT NULL,
  `vat_25` decimal(13,2) DEFAULT NULL,
  `vat_12` decimal(13,2) DEFAULT NULL,
  `vat_6` decimal(13,2) DEFAULT NULL,
  `vat_0` decimal(13,2) DEFAULT NULL,
  `amount_to_pay` decimal(13,2) DEFAULT NULL,
  `reported_vat` decimal(13,2) DEFAULT NULL,
  `next_invoice` date DEFAULT NULL,
  `note_1` text,
  `note_2` text,
  `note_3` text,
  `note_4` text,
  `note_5` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Tabellstruktur `creditcard_invoice_items`
--

CREATE TABLE `creditcard_invoice_items` (
  `id` bigint UNSIGNED NOT NULL,
  `main_id` bigint UNSIGNED NOT NULL,
  `line_no` int NOT NULL,
  `transaction_id` varchar(64) DEFAULT NULL,
  `purchase_date` date DEFAULT NULL,
  `posting_date` date DEFAULT NULL,
  `merchant_name` varchar(200) DEFAULT NULL,
  `merchant_city` varchar(100) DEFAULT NULL,
  `merchant_country` char(2) DEFAULT NULL,
  `mcc` varchar(4) DEFAULT NULL,
  `description` text,
  `currency_original` char(3) DEFAULT NULL,
  `amount_original` decimal(13,2) DEFAULT NULL,
  `exchange_rate` decimal(18,6) DEFAULT NULL,
  `amount_sek` decimal(13,2) DEFAULT NULL,
  `vat_rate` decimal(5,2) DEFAULT NULL,
  `vat_amount` decimal(13,2) DEFAULT NULL,
  `net_amount` decimal(13,2) DEFAULT NULL,
  `gross_amount` decimal(13,2) DEFAULT NULL,
  `cost_center_override` varchar(100) DEFAULT NULL,
  `project_code` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Tabellstruktur `creditcard_receipt_matches`
--

CREATE TABLE `creditcard_receipt_matches` (
  `id` bigint NOT NULL,
  `receipt_id` varchar(36) NOT NULL,
  `invoice_item_id` bigint UNSIGNED NOT NULL,
  `matched_amount` decimal(13,2) DEFAULT NULL,
  `matched_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Tabellstruktur `file_categories`
--

CREATE TABLE `file_categories` (
  `id` int NOT NULL,
  `name` varchar(222) NOT NULL,
  `description` varchar(222) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Tabellstruktur `file_locations`
--

CREATE TABLE `file_locations` (
  `id` bigint NOT NULL,
  `file_id` varchar(36) NOT NULL,
  `lat` double DEFAULT NULL,
  `lon` double DEFAULT NULL,
  `acc` double DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `file_locations`
--

INSERT INTO `file_locations` (`id`, `file_id`, `lat`, `lon`, `acc`, `created_at`) VALUES
(1, '260eff03-ce39-4218-aed7-a0207b4883b7', 59.41979876795737, 17.954478064972214, NULL, '2025-10-02 14:25:15'),
(2, 'd6173f97-95d1-4aa7-8ae2-70bdd7e447a4', 59.352693870029576, 17.96104917977293, NULL, '2025-10-02 14:25:16'),
(3, '77033392-3f8e-4679-88ff-051405f5ff39', 59.353184472725225, 17.961222771488764, NULL, '2025-10-02 14:25:16'),
(4, '595466b8-ed50-4a98-a248-8760aa14abb1', 59.353466610545155, 17.961097404122828, NULL, '2025-10-02 14:25:17'),
(5, '6495a8b5-7a4f-410f-90c0-3ff0b46d2614', 59.41976478152312, 17.954069748680578, NULL, '2025-10-02 14:25:17'),
(6, 'c1d28ed8-e733-42e2-ace6-5c3c796a9263', 59.35269151661247, 17.96099525649056, NULL, '2025-10-02 14:25:18'),
(7, 'b89b6b81-3b0b-44bd-ad44-31e3c40eb063', 59.3527166818701, 17.960909556687838, NULL, '2025-10-02 14:25:18'),
(8, '8b8bae38-1e69-4c21-98b8-c3fcf968410f', 59.35087093052369, 17.96826839447022, NULL, '2025-10-02 14:25:19'),
(9, '88809954-11ec-4708-a932-e6566adfec72', 59.35269146104154, 17.961066321759077, NULL, '2025-10-02 14:25:19');

-- --------------------------------------------------------

--
-- Tabellstruktur `file_suffix`
--

CREATE TABLE `file_suffix` (
  `id` int NOT NULL,
  `file_ending` varchar(255) NOT NULL,
  `file_type` int NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `file_suffix`
--

INSERT INTO `file_suffix` (`id`, `file_ending`, `file_type`, `created_at`) VALUES
(1, 'jpg', 1, '2025-09-30 14:50:40'),
(2, 'jpeg', 1, '2025-09-30 14:50:40'),
(3, 'png', 1, '2025-09-30 14:50:40'),
(4, 'mp4', 4, '2025-09-30 14:50:40'),
(5, 'mkv', 4, '2025-09-30 14:50:40'),
(6, 'gif', 1, '2025-09-30 14:50:40'),
(7, 'webp', 1, '2025-09-30 14:50:40'),
(8, 'mp3', 2, '2025-09-30 14:50:40'),
(9, 'wav', 2, '2025-09-30 14:50:40'),
(10, 'doc', 5, '2025-09-30 14:50:40'),
(11, 'docx', 5, '2025-09-30 14:50:40'),
(12, 'pdf', 5, '2025-09-30 14:50:40'),
(13, 'txt', 5, '2025-09-30 14:50:40'),
(14, 'json', 5, '2025-09-30 14:50:40');

-- --------------------------------------------------------

--
-- Tabellstruktur `file_tags`
--

CREATE TABLE `file_tags` (
  `file_id` varchar(36) NOT NULL,
  `tag` varchar(64) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `file_tags`
--

INSERT INTO `file_tags` (`file_id`, `tag`, `created_at`) VALUES
('260eff03-ce39-4218-aed7-a0207b4883b7', '2', '2025-10-02 14:25:15'),
('595466b8-ed50-4a98-a248-8760aa14abb1', '2', '2025-10-02 14:25:17'),
('6495a8b5-7a4f-410f-90c0-3ff0b46d2614', '9', '2025-10-02 14:25:17'),
('77033392-3f8e-4679-88ff-051405f5ff39', '2', '2025-10-02 14:25:16'),
('88809954-11ec-4708-a932-e6566adfec72', '2', '2025-10-02 14:25:19'),
('8b8bae38-1e69-4c21-98b8-c3fcf968410f', '2', '2025-10-02 14:25:19'),
('b89b6b81-3b0b-44bd-ad44-31e3c40eb063', '2', '2025-10-02 14:25:18'),
('c1d28ed8-e733-42e2-ace6-5c3c796a9263', '2', '2025-10-02 14:25:18'),
('d6173f97-95d1-4aa7-8ae2-70bdd7e447a4', '2', '2025-10-02 14:25:16');

-- --------------------------------------------------------

--
-- Tabellstruktur `invoice_documents`
--

CREATE TABLE `invoice_documents` (
  `id` varchar(36) NOT NULL,
  `invoice_type` varchar(32) NOT NULL,
  `period_start` date DEFAULT NULL,
  `period_end` date DEFAULT NULL,
  `uploaded_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `status` varchar(32) NOT NULL DEFAULT 'imported',
  `metadata_json` json DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Tabellstruktur `invoice_lines`
--

CREATE TABLE `invoice_lines` (
  `id` bigint NOT NULL,
  `invoice_id` varchar(36) NOT NULL,
  `transaction_date` date DEFAULT NULL,
  `amount` decimal(12,2) DEFAULT NULL,
  `merchant_name` varchar(255) DEFAULT NULL,
  `description` varchar(1024) DEFAULT NULL,
  `matched_file_id` varchar(36) DEFAULT NULL,
  `match_score` float DEFAULT NULL,
  `match_status` varchar(16) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Tabellstruktur `invoice_line_history`
--

CREATE TABLE `invoice_line_history` (
  `id` bigint NOT NULL,
  `invoice_line_id` bigint NOT NULL,
  `action` varchar(16) NOT NULL,
  `performed_by` varchar(64) DEFAULT NULL,
  `old_matched_file_id` varchar(36) DEFAULT NULL,
  `new_matched_file_id` varchar(36) DEFAULT NULL,
  `reason` varchar(1024) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Tabellstruktur `receipt_items`
--

CREATE TABLE `receipt_items` (
  `id` int NOT NULL,
  `main_id` varchar(36) NOT NULL COMMENT 'References unified_files.id',
  `article_id` varchar(222) DEFAULT NULL,
  `name` varchar(222) NOT NULL,
  `number` int NOT NULL,
  `item_price_ex_vat` decimal(10,2) DEFAULT NULL,
  `item_price_inc_vat` decimal(10,2) DEFAULT NULL,
  `item_total_price_ex_vat` decimal(10,2) DEFAULT NULL,
  `item_total_price_inc_vat` decimal(10,2) DEFAULT NULL,
  `currency` varchar(11) NOT NULL DEFAULT 'SEK',
  `vat` decimal(10,2) DEFAULT NULL,
  `vat_percentage` decimal(7,6) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `receipt_items`
--

INSERT INTO `receipt_items` (`id`, `main_id`, `article_id`, `name`, `number`, `item_price_ex_vat`, `item_price_inc_vat`, `item_total_price_ex_vat`, `item_total_price_inc_vat`, `currency`, `vat`, `vat_percentage`) VALUES
(3, '914003da-5688-458b-9f44-c44fe39c9daa', '', '', 6, 680.00, 680.00, 4080.00, 4080.00, 'SEK', 0.00, 0.000000),
(4, '44fd3255-8180-47c8-a5e9-256f19abdcae', '', '2', 5, 6090.00, 6090.00, 30450.00, 30450.00, 'SEK', 0.00, 0.000000),
(7, 'bbeb3dcb-d25c-4adb-8a69-0f320b02cc43', '', '', 6, 680.00, 680.00, 4080.00, 4080.00, 'SEK', 0.00, 0.000000),
(8, 'ae879afe-69f6-4078-94e5-cef7f3624b15', '', '2', 5, 6090.00, 6090.00, 30450.00, 30450.00, 'SEK', 0.00, 0.000000),
(11, '43f78437-7ac6-4724-bd3a-1bba90ac6b63', '', '', 6, 680.00, 680.00, 4080.00, 4080.00, 'SEK', 0.00, 0.000000),
(12, '1fff97d3-dedf-4d62-bd7b-44f7ec80db3f', '', '2', 5, 6090.00, 6090.00, 30450.00, 30450.00, 'SEK', 0.00, 0.000000),
(15, '47518a60-893e-4e2b-88d0-23a95c1f4dc3', '', '', 6, 680.00, 680.00, 4080.00, 4080.00, 'SEK', 0.00, 0.000000),
(16, 'c8df4525-849d-47dd-942f-f05693fa6a21', '', '2', 5, 6090.00, 6090.00, 30450.00, 30450.00, 'SEK', 0.00, 0.000000),
(19, 'e0cb0183-00d3-4eb9-84e4-639f972de0ac', '', '', 6, 680.00, 680.00, 4080.00, 4080.00, 'SEK', 0.00, 0.000000),
(20, 'c5bbd7db-4e8c-4b6a-885f-298eee0f27f7', '', '2', 5, 6090.00, 6090.00, 30450.00, 30450.00, 'SEK', 0.00, 0.000000),
(23, '3070f39a-229f-4827-9085-ec07ee5b730c', '', '', 6, 680.00, 680.00, 4080.00, 4080.00, 'SEK', 0.00, 0.000000),
(24, '9babbb97-06c8-4adc-a6ae-ca4c8903941c', '', '2', 5, 6090.00, 6090.00, 30450.00, 30450.00, 'SEK', 0.00, 0.000000),
(27, 'd34ba425-db67-4056-a0ce-cf9989b5671e', '', '', 6, 680.00, 680.00, 4080.00, 4080.00, 'SEK', 0.00, 0.000000),
(28, '741ab0aa-1bc3-470d-9071-a02419a69590', '', '2', 5, 6090.00, 6090.00, 30450.00, 30450.00, 'SEK', 0.00, 0.000000),
(29, 'ab40c2a7-1ee9-430f-b01c-9e885e34eb61', '', '', 6, 680.00, 680.00, 4080.00, 4080.00, 'SEK', 0.00, 0.000000),
(30, 'f14bdfcd-bef0-46b8-aea1-0116b33212ca', '', '2', 5, 6090.00, 6090.00, 30450.00, 30450.00, 'SEK', 0.00, 0.000000),
(41, 'e928f11f-4b33-4297-aa5b-81792f891531', '7318140010944', 'TUNNA 75L', 1, 191.20, 239.00, 191.20, 239.00, 'SEK', 47.80, 0.250000),
(42, 'e928f11f-4b33-4297-aa5b-81792f891531', '7318140010951', 'LOCK TILL TUNNA 75L', 1, 59.20, 74.00, 59.20, 74.00, 'SEK', 14.80, 0.250000),
(44, 'e416e090-845f-436b-b72e-0dd3bd9042a4', '24490', 'Airpods Pro, Gen 2 USB-C - Magsafe', 1, 2384.00, 2980.00, 2384.00, 2980.00, 'SEK', 596.00, 0.250000),
(45, 'd6173f97-95d1-4aa7-8ae2-70bdd7e447a4', '', 'Con Carne Rigatoni Original 33cl Coca-Cola', 1, NULL, 220.00, NULL, 220.00, 'SEK', NULL, NULL),
(46, 'd6173f97-95d1-4aa7-8ae2-70bdd7e447a4', '', 'Con Carne Rigatoni Coca-Cola Zero 33cl', 1, NULL, 220.00, NULL, 220.00, 'SEK', NULL, NULL),
(47, 'd6173f97-95d1-4aa7-8ae2-70bdd7e447a4', '', 'Con Carne Rigatoni Coca-Cola Zero 33cl', 1, NULL, 220.00, NULL, 220.00, 'SEK', NULL, NULL),
(48, '595466b8-ed50-4a98-a248-8760aa14abb1', '', 'Köp', 1, NULL, 358.90, NULL, 358.90, 'SEK', NULL, NULL),
(49, '77033392-3f8e-4679-88ff-051405f5ff39', '', 'Unknown item', 1, 209.44, 261.80, 209.44, 261.80, 'SEK', 52.36, 0.250000),
(50, '8b8bae38-1e69-4c21-98b8-c3fcf968410f', '', 'Rigatoni Con Carne + Coca Cola Original 33cl', 1, NULL, 220.00, NULL, 220.00, 'SEK', NULL, NULL),
(51, '8b8bae38-1e69-4c21-98b8-c3fcf968410f', '', 'Rigatoni Con Carne + Coca Cola Zero 33cl', 1, NULL, 220.00, NULL, 220.00, 'SEK', NULL, NULL),
(52, '8b8bae38-1e69-4c21-98b8-c3fcf968410f', '', 'Rigatoni Con Carne + Coca Cola Zero 33cl', 1, NULL, 220.00, NULL, 220.00, 'SEK', NULL, NULL),
(53, '88809954-11ec-4708-a932-e6566adfec72', '', 'KÖP', 1, NULL, 84.95, NULL, 84.95, 'SEK', NULL, NULL),
(54, 'b89b6b81-3b0b-44bd-ad44-31e3c40eb063', '7318140010944', 'TUNNA 75L', 1, 191.20, 239.00, 191.20, 239.00, 'SEK', 47.80, 0.250000),
(55, 'b89b6b81-3b0b-44bd-ad44-31e3c40eb063', '7318140010951', 'LOCK TILL TUNNA 75L', 1, 59.20, 74.00, 59.20, 74.00, 'SEK', 14.80, 0.250000);

-- --------------------------------------------------------

--
-- Tabellstruktur `tags`
--

CREATE TABLE `tags` (
  `id` int NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `description` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `tag_category` int NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Tabellstruktur `tag_categories`
--

CREATE TABLE `tag_categories` (
  `id` int NOT NULL,
  `tag_category_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `tag_category_description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Tabellstruktur `unified_files`
--

CREATE TABLE `unified_files` (
  `id` varchar(36) NOT NULL,
  `file_type` varchar(32) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT NULL,
  `orgnr` varchar(32) DEFAULT NULL,
  `payment_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Enter "cash" or "card"',
  `purchase_datetime` datetime DEFAULT NULL,
  `expense_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'If this is bought using a private card or cash (personal) or if it is corporate card (corporate)',
  `gross_amount_original` decimal(12,2) DEFAULT NULL COMMENT 'amount inc vat',
  `net_amount_original` decimal(12,2) DEFAULT NULL COMMENT 'amount ex vat',
  `exchange_rate` decimal(12,0) DEFAULT '0' COMMENT 'exchange rate example: 1 USD=11.33 SEK',
  `currency` varchar(222) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT 'SEK' COMMENT 'currency that was bought in',
  `gross_amount_sek` decimal(10,0) DEFAULT '0' COMMENT 'only used for foreign currency - shows the gross amount in sek',
  `net_amount_sek` decimal(10,0) DEFAULT '0' COMMENT 'The net amount in SEK after exchange conversion',
  `gross_amount` decimal(12,2) DEFAULT NULL,
  `net_amount` decimal(12,2) DEFAULT NULL,
  `ai_status` varchar(32) DEFAULT NULL,
  `ai_confidence` float DEFAULT NULL,
  `submitted_by` varchar(64) DEFAULT NULL,
  `original_filename` varchar(255) DEFAULT NULL,
  `original_file_id` varchar(36) DEFAULT NULL COMMENT 'Original file ID from FTP source',
  `original_file_name` varchar(222) DEFAULT NULL COMMENT 'Original filename from FTP source',
  `file_creation_timestamp` timestamp NULL DEFAULT NULL COMMENT 'File creation timestamp from FTP metadata',
  `original_file_size` int DEFAULT NULL COMMENT 'Original file size in bytes',
  `mime_type` varchar(222) DEFAULT NULL COMMENT 'MIME type of the original file',
  `ocr_raw` text NOT NULL DEFAULT (_latin1'') COMMENT 'The raw ocr-text without coordinates from the picture',
  `company_id` int DEFAULT '0' COMMENT 'companies.id - refering to the company that sold the product',
  `receipt_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'the unique receipt number',
  `file_suffix` varchar(32) DEFAULT NULL COMMENT 'File extension without dot',
  `file_category` int DEFAULT NULL COMMENT 'Reference to file_categories.id',
  `approved_by` int DEFAULT '0' COMMENT 'user id that approved the receipt',
  `other_data` text NOT NULL DEFAULT (_latin1'') COMMENT 'This is for all other data available on the receipt that doesnt have a specified column',
  `credit_card_match` tinyint(1) DEFAULT '0' COMMENT 'When matching receipt is available set 1',
  `content_hash` varchar(64) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `unified_files`
--

INSERT INTO `unified_files` (`id`, `file_type`, `created_at`, `updated_at`, `orgnr`, `payment_type`, `purchase_datetime`, `expense_type`, `gross_amount_original`, `net_amount_original`, `exchange_rate`, `currency`, `gross_amount_sek`, `net_amount_sek`, `gross_amount`, `net_amount`, `ai_status`, `ai_confidence`, `submitted_by`, `original_filename`, `original_file_id`, `original_file_name`, `file_creation_timestamp`, `original_file_size`, `mime_type`, `ocr_raw`, `company_id`, `receipt_number`, `file_suffix`, `file_category`, `approved_by`, `other_data`, `credit_card_match`, `content_hash`) VALUES
('260eff03-ce39-4218-aed7-a0207b4883b7', 'Manual Review', '2025-10-02 14:25:15', '2025-10-02 14:28:49', NULL, NULL, NULL, 'personal', NULL, NULL, 0, 'SEK', 0, 0, NULL, NULL, 'ai4_completed', 0.65, 'ftp', 'photo_68bdc1cc97f643.62743853.jpg', '9', 'photo_1757266379984_1.jpg', '2025-09-07 19:33:00', 1629839, 'image/jpeg', '', 0, NULL, 'jpg', 1, 0, '{}', 0, 'c0e6ea569eb30475bde243fb3c208930d83387d5038de63351806a2fa96f7596'),
('595466b8-ed50-4a98-a248-8760aa14abb1', 'receipt', '2025-10-02 14:25:17', '2025-10-02 14:29:29', NULL, 'card', '2025-09-08 08:40:00', 'corporate', 358.90, NULL, 0, 'SEK', 359, 0, NULL, NULL, 'ai5_no_match', 0.85, 'ftp', 'photo_68be7ad9d1e7c3.81863965.jpg', '10', 'photo_1757313753128_1.jpg', '2025-09-08 08:42:33', 2142684, 'image/jpeg', 'SE\nMS\nHandelsban\n30308472\nBUTIKSNR:\nTERM:\n40956913-1073220\n2025-09-08 08:40\nVisa\nDEBIT\nContactless\n***********3632-0\nAID: A0000000031010\nTVR: 0000000000\nREF: 517982 135108 KF1\nRESP: 00\nPERIOD: 750\nKöP\n358.90\nSEK\nGODKÄNT\n8 3\n303\nBAUHAUS\n16867 Bromma\nSA', 6, '517982 135108 KF1', 'jpg', 1, 0, '{\"terminal\":\"40956913-1073220\",\"aid\":\"A0000000031010\",\"card_mask\":\"***********3632-0\",\"ref\":\"517982 135108 KF1\",\"resp\":\"00\",\"period\":\"750\"}', 0, 'ab9061e7f57851ff859c05ae113b09926105078d140a7024a35043a12ef82e2e'),
('6495a8b5-7a4f-410f-90c0-3ff0b46d2614', 'other', '2025-10-02 14:25:17', '2025-10-02 14:29:01', NULL, NULL, NULL, 'personal', NULL, NULL, 0, 'SEK', 0, 0, NULL, NULL, 'ai4_completed', 0.65, 'ftp', 'photo_68b4a0e12436a2.02743784.jpg', '1', 'photo_1756668128632_1.jpg', '2025-08-31 21:22:09', 1169356, 'image/jpeg', 'aekcat\nVRPTEN\nENO\non', 0, NULL, 'jpg', 1, 0, '{}', 0, 'f9c254e178e48b220f43ff24db95acc83fa109c3e4cfc48e9f873fc6bc3911b9'),
('77033392-3f8e-4679-88ff-051405f5ff39', 'receipt', '2025-10-02 14:25:16', '2025-10-02 14:29:38', NULL, 'card', '2025-09-06 13:46:00', 'personal', 261.80, 209.44, 0, 'SEK', 262, 209, NULL, NULL, 'ai5_no_match', 0.65, 'ftp', 'photo_68bc1fcb8fb2d1.19853966.jpg', '7', 'photo_1757159367559_1.jpg', '2025-09-06 13:49:31', 2116861, 'image/jpeg', '123\n122\n8\nOGOORA\n261.80\nSER\nAAX\n824\nPERIOD :\n00\nRRRES\nRAT\n5102696\n392192\nPERS\nTVR: 0000000000\nwd\nAID: A0000000031010\nd\n0-2************\nContactless\nDEBIT\nBSIA\n13:46\n2025-09-06\n40956913-1073220\nAMA\n30308472\nBUTIKSNR :\n-\nES\nHandeIsban\nSW\n1138\n52 60 90\n113\n8\n111\n12367\n: ^2\nBetJänad\n261,80\n52,36\n25%\nBrutto\nMWMS\nMoms%\n2000140729\nA\"nueae\n0o\n011000210\n:Juapund\n261,80\nPoo\n261,80\nDOTO\n-12.95\nAAA\n159.00\nRA\nLSR\nSNCA\n11.600\nBOÄSO\nA709\nOO\n5069-029696\nOON MOE\naammn\n2989\n2\nKarIsbodavägen\nBAUHAUS', 0, '5102696', 'jpg', 1, 0, '{\"aid\":\"A0000000031010\",\"tvr\":\"0000000000\",\"masked_pan\":\"0-2************\",\"terminal\":\"30308472\"}', 0, 'a9edb34d2e091191aeeb9b2bb9301152423162ce88b94dccd7b5e284236368dc'),
('88809954-11ec-4708-a932-e6566adfec72', 'receipt', '2025-10-02 14:25:19', '2025-10-02 14:30:04', NULL, 'card', '2025-09-05 18:32:00', 'corporate', 84.95, NULL, 0, 'SEK', 85, 0, NULL, NULL, 'ai5_no_match', 0.85, 'ftp', 'photo_68bb122a63d1b1.20796996.jpg', '6', 'photo_1757090345580_1.jpg', '2025-09-05 18:39:06', 1891504, 'image/jpeg', 'SKA\nUTGANG\nMS\nHandelsban SE\nBUTIKSNR: _30308472\nTERM: 40956875-1073220\n2025-09-05 18:32\nVisa DEBIT\nContactless\n************3632-0\nAID: A0000000031010\nTVR: 0000000000\nREF: 577633 180359 KF1\nRESP: 00\nPERIOD: 747\nKÖP\n5\nSEK\n84.95\nGODKÄNT\n6  6 80\nBAUHAUS\n16867 Bromma', 6, '577633 180359 KF1', 'jpg', 1, 0, '{\"butiksnr\":\"30308472\",\"term\":\"40956875-1073220\",\"aid\":\"A0000000031010\",\"pan\":\"************3632-0\",\"tvr\":\"0000000000\",\"resp\":\"00\",\"ref\":\"577633 180359 KF1\"}', 0, 'ba61e4815c80549aaa64e1c125575f0110c2c1c0d17de6139f274c2afabd0c4f'),
('8b8bae38-1e69-4c21-98b8-c3fcf968410f', 'receipt', '2025-10-02 14:25:19', '2025-10-02 14:29:46', NULL, NULL, '2025-09-01 16:00:00', 'personal', 660.00, NULL, 0, 'SEK', 660, 0, NULL, NULL, 'ai5_no_match', 0.65, 'ftp', 'photo_68b5d14befd6b8.95349031.jpg', '4', 'photo_1756746059503_1.jpg', '2025-09-01 19:00:59', 1143142, 'image/jpeg', 'EJ kvitto\nUBEREATS\n#76868\nHenleverans\nFramne:\n2025-09-01 16:00\nNann:\nMattias\n8 580 970 68\nTel:\n+46\nTel\n76 273\nkod:\n168\n1x\n220.0\nRigatoni\nCon Carne\n* Coca Cola Originil 33c1\n1x\nRigatoni\n220,0\nCon\nCarne\nCoca Cola\nZero 33ol\n1x\nRigatoni\nCon Carne\n220,0\n+ Coca-Cola\nZero 33cl\nTotal:\n660,0 kr\nPgearad oy aupile', 0, '#76868', 'jpg', 1, 0, '{\"kod\":\"168\",\"note\":\"EJ kvitto\",\"delivery\":\"Henleverans\"}', 0, 'e5777f432af095978931690b22dfad62288bd318bc5f032b1b3d7a0f2af487fe'),
('b89b6b81-3b0b-44bd-ad44-31e3c40eb063', 'receipt', '2025-10-02 14:25:18', '2025-10-02 14:30:05', NULL, 'card', '2025-09-07 12:13:00', 'corporate', 313.00, 250.40, 0, 'SEK', 313, 250, NULL, NULL, 'ai5_no_match', 0.85, 'ftp', 'photo_68c39c92096163.69462592.jpg', '11', 'photo_1757650065365_1.jpg', '2025-09-12 06:07:46', 1871790, 'image/jpeg', 'HORNBACH\nDet\nfinns\nalltid\ngōra.\nnät\ntatt\nHornbach\nBy99marknad AB\nFilial\n773\nMadenvägen 17\n174 55 Sundbyber9\nTel. 08 - 799 50 00\nwww.hornbach.se\nMomsnr 556613-4853\n00\nART/EAN 7318140010944\n1 Styck\n×\n239,00\nTUNNA 75L\n239,00 1\nART/EAN 7318140010951\n1 Styck\n74,00\n×\nLOCK TILL TUNNA 75L\n74,00 1\nSumma [2]\nSEK\n313,00\nGIVET VISA\nSEK\n313,00\nHornbach Sundbyberg\nMadenvä9en 17\nSUNDBYBERG\nTel. Nr:\n087995000\nOrg.Nr:\n5566134853\n2025-09-07\n12:13\nKöP\nSEK 313.00\nVERIFIERAD AV ENHET\nVisa DEBIT\nPSN:00\nVISA CONTACTLESS\nXXXX XXXX XXXX 3632\nTERM:\n04709418-106957\n30574008\nKF1\nATC:01765\nAED:\nAID:\nA0000000031010\nARC:00\nSTATUS: 000\nAUKT.KOD:\n309300\nREF:106957\nResultat:\nAUKTORISERAD\nBEHALL KVITTOT\nKUNDENS KVITTO\nBRUTTO\nMOMS\nNETTO\n1 25 %\n313,00\n62,60\n250,40\n55507732509070046816\nÖppet köp 9äller 1 30 dagar,\ngäller obruten förpackning.\nBestälInings-/tillskurna varor,\nFiskar och växter ej öppet köp/eJ byte.\nSpara kvitto - galler som garanti.\n0773 2025-09-07 12:13 0004 000016 006816', 7, '30574008', 'jpg', 1, 0, '{\"terminal\":\"04709418-106957\",\"aid\":\"A0000000031010\",\"atc\":\"01765\",\"arc\":\"00\",\"ref\":\"106957\",\"auth_code\":\"309300\",\"psn\":\"00\",\"card_last4\":\"3632\"}', 0, 'fae9bf507129426a7997b12307cf4dac6ae2e9f1deebe2736238b10b84fbc8b6'),
('c1d28ed8-e733-42e2-ace6-5c3c796a9263', 'receipt', '2025-10-02 14:25:18', '2025-10-02 14:29:38', NULL, 'card', '2025-09-07 12:13:00', 'corporate', 313.00, 250.40, 0, 'AED', 0, 0, NULL, NULL, 'ai5_no_match', 0.85, 'ftp', 'photo_68d51dec3d2445.62262545.jpg', '12', 'photo_1758797291061_1.jpg', '2025-09-25 12:48:12', 2863045, 'image/jpeg', 'VERIFIERAD AV ENHET\nDEBIT\nPSN:00\nVisa\nVISA CONTACTLESS\n3632\nXXXX XXXX XXXX\n04709418-106957\nTERM\n30574008\nKF1\nATC:01765\nAED\nA0000000031010\nAID:\nSTATUS : 000\nARC:00\nAUKT.KOD:\n309300\nREF: 106957\nAUKTORISERAD\nResultat:\nBEHALL\nKVITTOT\nKUNDENS\nKVITTO\nBRUTTO\n1 25 %\n313,00\nMOMS\nNETTO\n62,60\n250,40\n55507732509070046816\nÖppet köp 9aller 1\ngaller obruten förPackning\n30\ndagar\nvaror\nSpara kvitto - galler\nbyte\n> Datum = leverans-\nSOM\n0773 2025-09-07 12:13 0004\noch\ngaranti\n0000\n<<', 0, '106957', 'jpg', 1, 0, '{\"terminal\":\"30574008\",\"aid\":\"A0000000031010\",\"atc\":\"01765\",\"arc\":\"00\",\"auth_code\":\"309300\",\"ref\":\"106957\",\"psn\":\"00\",\"status\":\"000\",\"card\":\"VISA\",\"last4\":\"3632\",\"raw_ref\":\"04709418-106957\"}', 0, '3ae2e5f808a0893cd7d4b8113fec4d031293104dc898f7768a7ac7736bce64a5'),
('d6173f97-95d1-4aa7-8ae2-70bdd7e447a4', 'receipt', '2025-10-02 14:25:16', '2025-10-02 14:29:17', NULL, NULL, '2025-09-01 16:00:00', 'personal', 660.00, NULL, 0, 'SEK', 660, 0, NULL, NULL, 'ai5_no_match', 0.65, 'ftp', 'photo_68b6739890f7a7.62128365.jpg', '5', 'photo_1756787608133_1.jpg', '2025-09-02 06:33:28', 2185897, 'image/jpeg', 'Ej\nkvitto\nUBEREATS\n#76868\nHemleverans\n16:00\n2025-09-01\nFramme:\nMattias\nNamn:\n8 586 970 68\n+46\nTel:\n76\n273\nkod:\n168\nTel\n1x\n220,0\nCon\nCarne\nRigatoni\nOriginal 33cl\nCoca-Cola\n1x\n220,0\nCon\nn Carne\nRigatoni\nCoca-Cola Zero 33cl\n1x\nCon Carne\n220,0\nRigatoni\nCoca-Cola Zero 33cl\n660,0 kr\nTotal:\nPauared by Qopla', 0, NULL, 'jpg', 1, 0, '{}', 0, 'c5755c411da6559174fe9e44b99c6ceb06f07ebd655713e8baae4edabb5a371e');

--
-- Index för dumpade tabeller
--

--
-- Index för tabell `ai_accounting_proposals`
--
ALTER TABLE `ai_accounting_proposals`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_ai_accounting_proposals_receipt` (`receipt_id`);

--
-- Index för tabell `ai_llm`
--
ALTER TABLE `ai_llm`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_ai_llm_enabled` (`enabled`);

--
-- Index för tabell `ai_llm_model`
--
ALTER TABLE `ai_llm_model`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_llm_model` (`llm_id`,`model_name`),
  ADD KEY `idx_ai_llm_model_llm_id` (`llm_id`),
  ADD KEY `idx_ai_llm_model_active` (`is_active`);

--
-- Index för tabell `ai_processing_history`
--
ALTER TABLE `ai_processing_history`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_file_stage` (`file_id`,`ai_stage_name`),
  ADD KEY `idx_status` (`status`);

--
-- Index för tabell `ai_processing_queue`
--
ALTER TABLE `ai_processing_queue`
  ADD PRIMARY KEY (`id`);

--
-- Index för tabell `ai_system_prompts`
--
ALTER TABLE `ai_system_prompts`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `prompt_key` (`prompt_key`),
  ADD KEY `selected_model_id` (`selected_model_id`);

--
-- Index för tabell `chart_of_accounts`
--
ALTER TABLE `chart_of_accounts`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_main_account` (`main_account`),
  ADD KEY `idx_sub_account` (`sub_account`);

--
-- Index för tabell `companies`
--
ALTER TABLE `companies`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ux_companies_orgnr` (`orgnr`);

--
-- Index för tabell `creditcard_invoices_main`
--
ALTER TABLE `creditcard_invoices_main`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ux_creditcard_invoices_number` (`invoice_number`),
  ADD KEY `ix_creditcard_invoices_date` (`invoice_date`),
  ADD KEY `ix_creditcard_invoices_number_long` (`invoice_number_long`);

--
-- Index för tabell `creditcard_invoice_items`
--
ALTER TABLE `creditcard_invoice_items`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ux_creditcard_invoice_line` (`main_id`,`line_no`),
  ADD KEY `ix_creditcard_invoice_purchase_date` (`purchase_date`),
  ADD KEY `ix_creditcard_invoice_merchant` (`merchant_name`);

--
-- Index för tabell `creditcard_receipt_matches`
--
ALTER TABLE `creditcard_receipt_matches`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ux_receipt_invoice_item` (`receipt_id`,`invoice_item_id`),
  ADD KEY `fk_receipt_matches_item` (`invoice_item_id`);

--
-- Index för tabell `file_categories`
--
ALTER TABLE `file_categories`
  ADD PRIMARY KEY (`id`);

--
-- Index för tabell `file_locations`
--
ALTER TABLE `file_locations`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_file_locations_file` (`file_id`);

--
-- Index för tabell `file_suffix`
--
ALTER TABLE `file_suffix`
  ADD PRIMARY KEY (`id`);

--
-- Index för tabell `file_tags`
--
ALTER TABLE `file_tags`
  ADD PRIMARY KEY (`file_id`,`tag`);

--
-- Index för tabell `invoice_documents`
--
ALTER TABLE `invoice_documents`
  ADD PRIMARY KEY (`id`);

--
-- Index för tabell `invoice_lines`
--
ALTER TABLE `invoice_lines`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_invoice_lines_doc` (`invoice_id`);

--
-- Index för tabell `invoice_line_history`
--
ALTER TABLE `invoice_line_history`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_line_history_line` (`invoice_line_id`);

--
-- Index för tabell `receipt_items`
--
ALTER TABLE `receipt_items`
  ADD PRIMARY KEY (`id`);

--
-- Index för tabell `tags`
--
ALTER TABLE `tags`
  ADD PRIMARY KEY (`id`);

--
-- Index för tabell `tag_categories`
--
ALTER TABLE `tag_categories`
  ADD PRIMARY KEY (`id`);

--
-- Index för tabell `unified_files`
--
ALTER TABLE `unified_files`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `idx_content_hash` (`content_hash`),
  ADD KEY `idx_unified_files_creation_timestamp` (`file_creation_timestamp`),
  ADD KEY `idx_unified_files_original_file_id` (`original_file_id`);

--
-- AUTO_INCREMENT för dumpade tabeller
--

--
-- AUTO_INCREMENT för tabell `ai_accounting_proposals`
--
ALTER TABLE `ai_accounting_proposals`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT för tabell `ai_llm`
--
ALTER TABLE `ai_llm`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT för tabell `ai_llm_model`
--
ALTER TABLE `ai_llm_model`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT för tabell `ai_processing_history`
--
ALTER TABLE `ai_processing_history`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=73;

--
-- AUTO_INCREMENT för tabell `ai_processing_queue`
--
ALTER TABLE `ai_processing_queue`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT för tabell `ai_system_prompts`
--
ALTER TABLE `ai_system_prompts`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT för tabell `chart_of_accounts`
--
ALTER TABLE `chart_of_accounts`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1319;

--
-- AUTO_INCREMENT för tabell `companies`
--
ALTER TABLE `companies`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT för tabell `creditcard_invoices_main`
--
ALTER TABLE `creditcard_invoices_main`
  MODIFY `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT för tabell `creditcard_invoice_items`
--
ALTER TABLE `creditcard_invoice_items`
  MODIFY `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT för tabell `creditcard_receipt_matches`
--
ALTER TABLE `creditcard_receipt_matches`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT för tabell `file_categories`
--
ALTER TABLE `file_categories`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT för tabell `file_locations`
--
ALTER TABLE `file_locations`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT för tabell `file_suffix`
--
ALTER TABLE `file_suffix`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=15;

--
-- AUTO_INCREMENT för tabell `invoice_lines`
--
ALTER TABLE `invoice_lines`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT för tabell `invoice_line_history`
--
ALTER TABLE `invoice_line_history`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT för tabell `receipt_items`
--
ALTER TABLE `receipt_items`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=56;

--
-- AUTO_INCREMENT för tabell `tags`
--
ALTER TABLE `tags`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT för tabell `tag_categories`
--
ALTER TABLE `tag_categories`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- Restriktioner för dumpade tabeller
--

--
-- Restriktioner för tabell `ai_llm_model`
--
ALTER TABLE `ai_llm_model`
  ADD CONSTRAINT `ai_llm_model_ibfk_1` FOREIGN KEY (`llm_id`) REFERENCES `ai_llm` (`id`) ON DELETE CASCADE;

--
-- Restriktioner för tabell `ai_system_prompts`
--
ALTER TABLE `ai_system_prompts`
  ADD CONSTRAINT `ai_system_prompts_ibfk_1` FOREIGN KEY (`selected_model_id`) REFERENCES `ai_llm_model` (`id`) ON DELETE SET NULL;

--
-- Restriktioner för tabell `creditcard_invoice_items`
--
ALTER TABLE `creditcard_invoice_items`
  ADD CONSTRAINT `fk_creditcard_items_main` FOREIGN KEY (`main_id`) REFERENCES `creditcard_invoices_main` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Restriktioner för tabell `creditcard_receipt_matches`
--
ALTER TABLE `creditcard_receipt_matches`
  ADD CONSTRAINT `fk_receipt_matches_item` FOREIGN KEY (`invoice_item_id`) REFERENCES `creditcard_invoice_items` (`id`) ON DELETE CASCADE;

--
-- Restriktioner för tabell `invoice_lines`
--
ALTER TABLE `invoice_lines`
  ADD CONSTRAINT `fk_invoice_lines_doc` FOREIGN KEY (`invoice_id`) REFERENCES `invoice_documents` (`id`);

--
-- Restriktioner för tabell `invoice_line_history`
--
ALTER TABLE `invoice_line_history`
  ADD CONSTRAINT `fk_line_history_line` FOREIGN KEY (`invoice_line_id`) REFERENCES `invoice_lines` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
