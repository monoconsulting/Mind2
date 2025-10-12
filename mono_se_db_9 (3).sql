-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Värd: mysql:3306
-- Tid vid skapande: 29 sep 2025 kl 10:10
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
  `item_id` int NOT NULL,
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
  `id` bigint UNSIGNED NOT NULL,
  `provider_name` varchar(100) NOT NULL,
  `own_name` varchar(255) DEFAULT NULL,
  `api_key` text,
  `endpoint_url` text,
  `enabled` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `ai_llm`
--

INSERT INTO `ai_llm` (`id`, `provider_name`, `own_name`, `api_key`, `endpoint_url`, `enabled`, `created_at`, `updated_at`) VALUES
(1, 'OpenAI', 'OpenAI', '', '', 1, '2025-09-28 16:19:39', '2025-09-28 16:19:39');

-- --------------------------------------------------------

--
-- Tabellstruktur `ai_llm_model`
--

CREATE TABLE `ai_llm_model` (
  `id` bigint UNSIGNED NOT NULL,
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
(1, 1, 'gpt-5', 'gpt-5', 1, '2025-09-28 16:22:08'),
(2, 1, 'gpt-4.1', 'gpt-4.1', 1, '2025-09-28 16:22:18'),
(3, 1, 'o4-mini', 'o4-mini', 1, '2025-09-28 16:22:27'),
(4, 1, 'gpt-audio', 'gpt-audio', 1, '2025-09-28 16:22:43'),
(5, 1, 'gpt-5-mini', 'gpt-5-mini', 1, '2025-09-28 16:23:05'),
(6, 1, 'gpt-5-nano', 'gpt-5-nano', 1, '2025-09-28 16:23:29');

-- --------------------------------------------------------

--
-- Tabellstruktur `ai_processing_history`
--

CREATE TABLE `ai_processing_history` (
  `id` bigint NOT NULL,
  `file_id` varchar(36) NOT NULL,
  `job_type` varchar(64) NOT NULL,
  `status` varchar(32) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `ai_processing_history`
--

INSERT INTO `ai_processing_history` (`id`, `file_id`, `job_type`, `status`, `created_at`) VALUES
(1, '744eab24-1d49-4705-a5d6-60aac05df151', 'ocr', 'success', '2025-09-28 17:42:32'),
(2, '9618aba4-6e2a-4c6a-8b6c-241aa825ca97', 'ocr', 'success', '2025-09-28 17:42:32'),
(3, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'ocr', 'success', '2025-09-28 17:42:32'),
(4, '22890eab-2f5d-4bc7-b881-41a9da740e45', 'ocr', 'success', '2025-09-28 17:42:32'),
(5, '9d3150fb-1c4e-446a-8610-1281fd9e5c4b', 'ocr', 'success', '2025-09-28 17:42:34'),
(6, '998ac2c2-caa3-472d-9b04-f21785711961', 'ocr', 'success', '2025-09-28 17:42:34'),
(7, 'b447ba44-4162-4450-851e-0fd1ddd78d42', 'ocr', 'success', '2025-09-28 17:42:34'),
(8, '361541f7-54de-4e45-bcc7-6a20d50135e6', 'ocr', 'success', '2025-09-28 17:42:35'),
(9, '010fc9ec-2cb6-436e-b73c-a82ce7c4026a', 'ocr', 'success', '2025-09-28 17:42:35'),
(10, '9618aba4-6e2a-4c6a-8b6c-241aa825ca97', 'classification', 'success', '2025-09-28 17:42:35'),
(11, '744eab24-1d49-4705-a5d6-60aac05df151', 'classification', 'success', '2025-09-28 17:42:36'),
(12, '22890eab-2f5d-4bc7-b881-41a9da740e45', 'classification', 'success', '2025-09-28 17:42:36'),
(13, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'classification', 'success', '2025-09-28 17:42:36'),
(14, 'b447ba44-4162-4450-851e-0fd1ddd78d42', 'classification', 'success', '2025-09-28 17:42:37'),
(15, '998ac2c2-caa3-472d-9b04-f21785711961', 'classification', 'success', '2025-09-28 17:42:37'),
(16, '9d3150fb-1c4e-446a-8610-1281fd9e5c4b', 'classification', 'success', '2025-09-28 17:42:37'),
(17, '361541f7-54de-4e45-bcc7-6a20d50135e6', 'classification', 'success', '2025-09-28 17:42:37'),
(18, '010fc9ec-2cb6-436e-b73c-a82ce7c4026a', 'classification', 'success', '2025-09-28 17:42:38'),
(19, '9618aba4-6e2a-4c6a-8b6c-241aa825ca97', 'validation', 'success', '2025-09-28 17:42:38'),
(20, '22890eab-2f5d-4bc7-b881-41a9da740e45', 'validation', 'success', '2025-09-28 17:42:38'),
(21, '744eab24-1d49-4705-a5d6-60aac05df151', 'validation', 'success', '2025-09-28 17:42:39'),
(22, 'b447ba44-4162-4450-851e-0fd1ddd78d42', 'validation', 'success', '2025-09-28 17:42:39'),
(23, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'validation', 'success', '2025-09-28 17:42:39'),
(24, '998ac2c2-caa3-472d-9b04-f21785711961', 'validation', 'success', '2025-09-28 17:42:40'),
(25, '9d3150fb-1c4e-446a-8610-1281fd9e5c4b', 'validation', 'success', '2025-09-28 17:42:40'),
(26, '361541f7-54de-4e45-bcc7-6a20d50135e6', 'validation', 'success', '2025-09-28 17:42:40'),
(27, '010fc9ec-2cb6-436e-b73c-a82ce7c4026a', 'validation', 'success', '2025-09-28 17:42:40'),
(28, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'ocr', 'success', '2025-09-28 18:35:30'),
(29, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'classification', 'success', '2025-09-28 18:35:30'),
(30, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'validation', 'success', '2025-09-28 18:35:30'),
(31, '9618aba4-6e2a-4c6a-8b6c-241aa825ca97', 'ocr', 'success', '2025-09-28 18:35:30'),
(32, '9618aba4-6e2a-4c6a-8b6c-241aa825ca97', 'classification', 'success', '2025-09-28 18:35:30'),
(33, '9618aba4-6e2a-4c6a-8b6c-241aa825ca97', 'validation', 'success', '2025-09-28 18:35:30'),
(34, '744eab24-1d49-4705-a5d6-60aac05df151', 'ocr', 'success', '2025-09-28 18:35:30'),
(35, '744eab24-1d49-4705-a5d6-60aac05df151', 'classification', 'success', '2025-09-28 18:35:30'),
(36, '744eab24-1d49-4705-a5d6-60aac05df151', 'validation', 'success', '2025-09-28 18:35:30'),
(37, '9d3150fb-1c4e-446a-8610-1281fd9e5c4b', 'ocr', 'success', '2025-09-28 18:35:30'),
(38, '9d3150fb-1c4e-446a-8610-1281fd9e5c4b', 'classification', 'success', '2025-09-28 18:35:30'),
(39, '9d3150fb-1c4e-446a-8610-1281fd9e5c4b', 'validation', 'success', '2025-09-28 18:35:30'),
(40, 'b447ba44-4162-4450-851e-0fd1ddd78d42', 'ocr', 'success', '2025-09-28 18:35:30'),
(41, 'b447ba44-4162-4450-851e-0fd1ddd78d42', 'classification', 'success', '2025-09-28 18:35:30'),
(42, 'b447ba44-4162-4450-851e-0fd1ddd78d42', 'validation', 'success', '2025-09-28 18:35:30'),
(43, '361541f7-54de-4e45-bcc7-6a20d50135e6', 'ocr', 'success', '2025-09-28 18:35:31'),
(44, '361541f7-54de-4e45-bcc7-6a20d50135e6', 'classification', 'success', '2025-09-28 18:35:31'),
(45, '361541f7-54de-4e45-bcc7-6a20d50135e6', 'validation', 'success', '2025-09-28 18:35:31'),
(46, '998ac2c2-caa3-472d-9b04-f21785711961', 'ocr', 'success', '2025-09-28 18:35:31'),
(47, '998ac2c2-caa3-472d-9b04-f21785711961', 'classification', 'success', '2025-09-28 18:35:31'),
(48, '998ac2c2-caa3-472d-9b04-f21785711961', 'validation', 'success', '2025-09-28 18:35:31'),
(49, '010fc9ec-2cb6-436e-b73c-a82ce7c4026a', 'ocr', 'success', '2025-09-28 18:35:31'),
(50, '010fc9ec-2cb6-436e-b73c-a82ce7c4026a', 'classification', 'success', '2025-09-28 18:35:31'),
(51, '010fc9ec-2cb6-436e-b73c-a82ce7c4026a', 'validation', 'success', '2025-09-28 18:35:31'),
(52, '22890eab-2f5d-4bc7-b881-41a9da740e45', 'ocr', 'success', '2025-09-28 18:35:31'),
(53, '22890eab-2f5d-4bc7-b881-41a9da740e45', 'classification', 'success', '2025-09-28 18:35:31'),
(54, '22890eab-2f5d-4bc7-b881-41a9da740e45', 'validation', 'success', '2025-09-28 18:35:31'),
(55, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'ocr', 'success', '2025-09-28 18:45:23'),
(56, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'classification', 'success', '2025-09-28 18:45:23'),
(57, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'validation', 'success', '2025-09-28 18:45:23'),
(58, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'ocr', 'success', '2025-09-28 18:45:42'),
(59, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'classification', 'success', '2025-09-28 18:45:42'),
(60, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'validation', 'success', '2025-09-28 18:45:42'),
(61, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'ocr', 'success', '2025-09-28 18:46:32'),
(62, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'classification', 'success', '2025-09-28 18:46:32'),
(63, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'validation', 'success', '2025-09-28 18:46:32'),
(64, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'ocr', 'success', '2025-09-28 18:47:55'),
(65, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'classification', 'success', '2025-09-28 18:47:55'),
(66, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'validation', 'success', '2025-09-28 18:47:56'),
(67, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'ocr', 'success', '2025-09-28 18:50:54'),
(68, '9d3150fb-1c4e-446a-8610-1281fd9e5c4b', 'ocr', 'success', '2025-09-28 18:51:00'),
(69, '744eab24-1d49-4705-a5d6-60aac05df151', 'ocr', 'success', '2025-09-28 18:51:17'),
(70, '9618aba4-6e2a-4c6a-8b6c-241aa825ca97', 'ocr', 'success', '2025-09-28 18:51:39'),
(71, '361541f7-54de-4e45-bcc7-6a20d50135e6', 'ocr', 'success', '2025-09-28 18:51:49'),
(72, 'b447ba44-4162-4450-851e-0fd1ddd78d42', 'ocr', 'success', '2025-09-28 18:52:15'),
(73, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'classification', 'success', '2025-09-28 18:52:15'),
(74, '9d3150fb-1c4e-446a-8610-1281fd9e5c4b', 'classification', 'success', '2025-09-28 18:52:16'),
(75, '744eab24-1d49-4705-a5d6-60aac05df151', 'classification', 'success', '2025-09-28 18:52:16'),
(76, '9618aba4-6e2a-4c6a-8b6c-241aa825ca97', 'classification', 'success', '2025-09-28 18:52:16'),
(77, '361541f7-54de-4e45-bcc7-6a20d50135e6', 'classification', 'success', '2025-09-28 18:52:16'),
(78, 'b447ba44-4162-4450-851e-0fd1ddd78d42', 'classification', 'success', '2025-09-28 18:52:16'),
(79, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 'validation', 'success', '2025-09-28 18:52:17'),
(80, '9d3150fb-1c4e-446a-8610-1281fd9e5c4b', 'validation', 'success', '2025-09-28 18:52:17'),
(81, '744eab24-1d49-4705-a5d6-60aac05df151', 'validation', 'success', '2025-09-28 18:52:17'),
(82, '9618aba4-6e2a-4c6a-8b6c-241aa825ca97', 'validation', 'success', '2025-09-28 18:52:17'),
(83, '361541f7-54de-4e45-bcc7-6a20d50135e6', 'validation', 'success', '2025-09-28 18:52:17'),
(84, 'b447ba44-4162-4450-851e-0fd1ddd78d42', 'validation', 'success', '2025-09-28 18:52:17'),
(85, '998ac2c2-caa3-472d-9b04-f21785711961', 'ocr', 'success', '2025-09-28 18:52:18'),
(86, '998ac2c2-caa3-472d-9b04-f21785711961', 'classification', 'success', '2025-09-28 18:52:19'),
(87, '998ac2c2-caa3-472d-9b04-f21785711961', 'validation', 'success', '2025-09-28 18:52:19'),
(88, '22890eab-2f5d-4bc7-b881-41a9da740e45', 'ocr', 'success', '2025-09-28 18:52:24'),
(89, '22890eab-2f5d-4bc7-b881-41a9da740e45', 'classification', 'success', '2025-09-28 18:52:24'),
(90, '22890eab-2f5d-4bc7-b881-41a9da740e45', 'validation', 'success', '2025-09-28 18:52:24'),
(91, '010fc9ec-2cb6-436e-b73c-a82ce7c4026a', 'ocr', 'success', '2025-09-28 18:52:25'),
(92, '010fc9ec-2cb6-436e-b73c-a82ce7c4026a', 'classification', 'success', '2025-09-28 18:52:25'),
(93, '010fc9ec-2cb6-436e-b73c-a82ce7c4026a', 'validation', 'success', '2025-09-28 18:52:25');

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
  `id` bigint UNSIGNED NOT NULL,
  `prompt_key` varchar(100) NOT NULL,
  `title` varchar(255) NOT NULL,
  `description` text,
  `prompt_content` text,
  `selected_model_id` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `ai_system_prompts`
--

INSERT INTO `ai_system_prompts` (`id`, `prompt_key`, `title`, `description`, `prompt_content`, `selected_model_id`, `created_at`, `updated_at`) VALUES
(1, 'document_analysis', 'Dokumentanalys', 'Analyserar kvitton, fakturor och andra dokument', 'You are an AI model that receives text from a scanned document. Determine what type of document it is: \"receipt\", \"invoice\", or \"other\". Focus on clues in the text (e.g., words like \"receipt payment\", \"VAT rate\", company names, reference numbers, format). Respond only with one of these three labels without any explanation.', 5, '2025-09-27 17:44:23', '2025-09-28 16:29:20'),
(2, 'expense_classification', 'Utlägg eller företag', 'AvgÃ¶r om ett kvitto Ã¤r ett personligt utlÃ¤gg eller fÃ¶retagskostnad', 'You are an AI model that analyzes a receipt’s details (payment method, card data, context). Determine whether the receipt is for a personal expense or a corporate card payment. Look for indicators such as company names, text like \"FirstCard\", or if the expense is linked to an employee. Respond with \"personal_expense\" or \"corporate\" with no additional text.', 5, '2025-09-27 17:44:23', '2025-09-29 06:34:27'),
(3, 'receipt_items_classification', 'Klassificering av kvittoposter', 'Kategoriserar och sorterar kvittodata', 'You receive OCR text from a Swedish receipt or invoice. Extract the following fields and return them in JSON format:\n', 1, '2025-09-27 17:44:23', '2025-09-29 06:34:57'),
(4, 'accounting', 'Kontering', 'Hanterar all konterings-relaterad information', 'You are an AI model that receives input: a receipt object with amounts and VAT information. Suggest accounting entries according to Swedish BAS 2025. Return a JSON list with objects containing:\n\naccount_code: BAS account number (e.g., \"2641\", \"4010\")\n\ndebit or credit: the amount (set either debit or credit)\n\nvat_rate: VAT rate for the item (e.g., 25.0)\n\nnotes: Short description of the accounting entry\n\nUse Swedish accounting rules (e.g., 2641 for input VAT 25%).', 1, '2025-09-27 17:44:23', '2025-09-28 16:33:20'),
(5, 'first_card', 'First Card', 'Matchar FirstCard-fakturor mot befintliga kvitton', 'You receive JSON data for a receipt and an invoice line from FirstCard. Determine if the receipt matches the invoice line. Compare amounts and merchant information. If the receipt matches the line, return JSON with \"match\": true and invoice_line_id; otherwise, \"match\": false.\n\n', NULL, '2025-09-27 17:44:23', '2025-09-28 16:34:03');

-- --------------------------------------------------------

--
-- Tabellstruktur `chart_of_accounts`
--

CREATE TABLE `chart_of_accounts` (
  `id` int DEFAULT NULL,
  `main_account` varchar(3) DEFAULT NULL,
  `main_account_description` varchar(153) DEFAULT NULL,
  `no_k2` varchar(1) DEFAULT NULL,
  `simple_account` varchar(1) DEFAULT NULL,
  `sub_account` varchar(4) DEFAULT NULL,
  `sub_account_description` varchar(153) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `chart_of_accounts`
--

INSERT INTO `chart_of_accounts` (`id`, `main_account`, `main_account_description`, `no_k2`, `simple_account`, `sub_account`, `sub_account_description`) VALUES
(1, '1', 'Tillgångar', '', '', '', ''),
(2, '10', 'Immateriella anläggningstillgångar', '', '', '', ''),
(3, '101', 'Utvecklingsutgifter', '1', '', '1010', 'Utvecklingsutgifter'),
(4, '101', 'Utvecklingsutgifter', '1', '', '1011', 'Balanserade utgifter för forskning och utveckling'),
(5, '101', 'Utvecklingsutgifter', '1', '', '1012', 'Balanserade utgifter för programvaror'),
(6, '101', 'Utvecklingsutgifter', '1', '', '1018', 'Ackumulerade nedskrivningar på balanserade utgifter'),
(7, '101', 'Utvecklingsutgifter', '1', '', '1019', 'Ackumulerade avskrivningar på balanserade utgifter'),
(8, '102', 'Koncessioner m.m.', '', '', '1020', 'Koncessioner m.m.'),
(9, '102', 'Koncessioner m.m.', '', '', '1028', 'Ackumulerade nedskrivningar på koncessioner m.m.'),
(10, '102', 'Koncessioner m.m.', '', '', '1029', 'Ackumulerade avskrivningar på koncessioner m.m.'),
(11, '103', 'Patent', '', '1', '1030', 'Patent'),
(12, '103', 'Patent', '', '', '1038', 'Ackumulerade nedskrivningar på patent'),
(13, '103', 'Patent', '', '1', '1039', 'Ackumulerade avskrivningar på patent'),
(14, '104', 'Licenser', '', '', '1040', 'Licenser'),
(15, '104', 'Licenser', '', '', '1048', 'Ackumulerade nedskrivningar på licenser'),
(16, '104', 'Licenser', '', '', '1049', 'Ackumulerade avskrivningar på licenser'),
(17, '105', 'Varumärken', '', '', '1050', 'Varumärken'),
(18, '105', 'Varumärken', '', '', '1058', 'Ackumulerade nedskrivningar på varumärken'),
(19, '105', 'Varumärken', '', '', '1059', 'Ackumulerade avskrivningar på varumärken'),
(20, '106', 'Hyresrätter, tomträtter och liknande', '', '1', '1060', 'Hyresrätter, tomträtter och liknande'),
(21, '106', 'Hyresrätter, tomträtter och liknande', '', '', '1068', 'Ackumulerade nedskrivningar på hyresrätter, tomträtter och liknande'),
(22, '106', 'Hyresrätter, tomträtter och liknande', '', '1', '1069', 'Ackumulerade avskrivningar på hyresrätter, tomträtter och liknande'),
(23, '107', 'Goodwill', '', '', '1070', 'Goodwill'),
(24, '107', 'Goodwill', '', '', '1078', 'Ackumulerade nedskrivningar på goodwill'),
(25, '107', 'Goodwill', '', '', '1079', 'Ackumulerade avskrivningar på goodwill'),
(26, '108', 'Förskott för immateriella anläggningstillgångar', '', '', '1080', 'Förskott för immateriella anläggningstillgångar'),
(27, '108', 'Förskott för immateriella anläggningstillgångar', '1', '', '1081', 'Pågående projekt för immateriella anläggningstillgångar'),
(28, '108', 'Förskott för immateriella anläggningstillgångar', '', '', '1088', 'Förskott för immateriella anläggningstillgångar'),
(29, '11', 'Byggnader och mark', '', '', '', ''),
(30, '111', 'Byggnader', '', '1', '1110', 'Byggnader'),
(31, '111', 'Byggnader', '', '', '1111', 'Byggnader på egen mark'),
(32, '111', 'Byggnader', '', '', '1112', 'Byggnader på annans mark'),
(33, '', 'Byggnader', '', '', '1118', 'Ackumulerade nedskrivningar på byggnader'),
(34, '', 'Byggnader', '', '1', '1119', 'Ackumulerade avskrivningar på byggnader'),
(35, '112', 'Förbättringsutgifter på annans fastighet', '', '', '1120', 'Förbättringsutgifter på annans fastighet'),
(36, '', 'Förbättringsutgifter på annans fastighet', '', '', '1129', 'Ackumulerade avskrivningar på förbättringsutgifter på annans fastighet'),
(37, '113', 'Mark', '', '1', '1130', 'Mark'),
(38, '114', 'Tomter och obebyggda markområden', '', '', '1140', 'Tomter och obebyggda markområden'),
(39, '115', 'Markanläggningar', '', '1', '1150', 'Markanläggningar'),
(40, '', 'Markanläggningar', '', '', '1158', 'Ackumulerade nedskrivningar på markanläggningar'),
(41, '', 'Markanläggningar', '', '1', '1159', 'Ackumulerade avskrivningar på markanläggningar'),
(42, '118', 'Pågående nyanläggningar och förskott för byggnader och mark', '', '', '1180', 'Pågående nyanläggningar och förskott för byggnader och mark'),
(43, '', 'Pågående nyanläggningar och förskott för byggnader och mark', '', '', '1181', 'Pågående ny-, till- och ombyggnad'),
(44, '', 'Pågående nyanläggningar och förskott för byggnader och mark', '', '', '1188', 'Förskott för byggnader och mark'),
(45, '12', 'Maskiner och inventarier', '', '', '', ''),
(46, '121', 'Maskiner och andra tekniska anläggningar', '', '1', '1210', 'Maskiner och andra tekniska anläggningar'),
(47, '', 'Maskiner och andra tekniska anläggningar', '', '', '1211', 'Maskiner'),
(48, '', 'Maskiner och andra tekniska anläggningar', '', '', '1213', 'Andra tekniska anläggningar'),
(49, '', 'Maskiner och andra tekniska anläggningar', '', '', '1218', 'Ackumulerade nedskrivningar på maskiner och andra tekniska anläggningar'),
(50, '', 'Maskiner och andra tekniska anläggningar', '', '1', '1219', 'Ackumulerade avskrivningar på maskiner och andra tekniska anläggningar'),
(51, '122', 'Inventarier och verktyg', '', '1', '1220', 'Inventarier och verktyg'),
(52, '', 'Inventarier och verktyg', '', '', '1221', 'Inventarier'),
(53, '', 'Inventarier och verktyg', '', '', '1222', 'Byggnadsinventarier'),
(54, '', 'Inventarier och verktyg', '', '', '1223', 'Markinventarier'),
(55, '', 'Inventarier och verktyg', '', '', '1225', 'Verktyg'),
(56, '', 'Inventarier och verktyg', '', '', '1228', 'Ackumulerade nedskrivningar på inventarier och verktyg'),
(57, '', 'Inventarier och verktyg', '', '1', '1229', 'Ackumulerade avskrivningar på inventarier och verktyg'),
(58, '123', 'Installationer', '', '', '1230', 'Installationer'),
(59, '', 'Installationer', '', '', '1231', 'Installationer på egen fastighet'),
(60, '', 'Installationer', '', '', '1232', 'Installationer på annans fastighet'),
(61, '', 'Installationer', '', '', '1238', 'Ackumulerade nedskrivningar på installationer'),
(62, '', 'Installationer', '', '', '1239', 'Ackumulerade avskrivningar på installationer'),
(63, '124', 'Bilar och andra transportmedel', '', '1', '1240', 'Bilar och andra transportmedel'),
(64, '', 'Bilar och andra transportmedel', '', '', '1241', 'Personbilar'),
(65, '', 'Bilar och andra transportmedel', '', '', '1242', 'Lastbilar'),
(66, '', 'Bilar och andra transportmedel', '', '', '1243', 'Truckar'),
(67, '', 'Bilar och andra transportmedel', '', '', '1244', 'Arbetsmaskiner'),
(68, '', 'Bilar och andra transportmedel', '', '', '1245', 'Traktorer'),
(69, '', 'Bilar och andra transportmedel', '', '', '1246', 'Motorcyklar, mopeder och skotrar'),
(70, '', 'Bilar och andra transportmedel', '', '', '1247', 'Båtar, flygplan och helikoptrar'),
(71, '', 'Bilar och andra transportmedel', '', '', '1248', 'Ackumulerade nedskrivningar på bilar och andra transportmedel'),
(72, '', 'Bilar och andra transportmedel', '', '1', '1249', 'Ackumulerade avskrivningar på bilar och andra transportmedel'),
(73, '125', 'Datorer', '', '1', '1250', 'Datorer'),
(74, '', 'Datorer', '', '', '1251', 'Datorer, företaget'),
(75, '', 'Datorer', '', '', '1257', 'Datorer, personal'),
(76, '', 'Datorer', '', '', '1258', 'Ackumulerade nedskrivningar på datorer'),
(77, '', 'Datorer', '', '1', '1259', 'Ackumulerade avskrivningar på datorer'),
(78, '126', 'Leasade tillgångar', '1', '', '1260', 'Leasade tillgångar'),
(79, '', 'Leasade tillgångar', '1', '', '1269', 'Ackumulerade avskrivningar på leasade tillgångar'),
(80, '128', 'Pågående nyanläggningar och förskott för maskiner och inventarier', '', '', '1280', 'Pågående nyanläggningar och förskott för maskiner och inventarier'),
(81, '', 'Pågående nyanläggningar och förskott för maskiner och inventarier', '', '', '1281', 'Pågående nyanläggningar, maskiner och inventarier'),
(82, '', 'Pågående nyanläggningar och förskott för maskiner och inventarier', '', '', '1288', 'Förskott för maskiner och inventarier'),
(83, '129', 'Övriga materiella anläggningstillgångar', '', '1', '1290', 'Övriga materiella anläggningstillgångar'),
(84, '', 'Övriga materiella anläggningstillgångar', '', '1', '1291', 'Konst och liknande tillgångar'),
(85, '', 'Övriga materiella anläggningstillgångar', '', '', '1292', 'Djur som klassificeras som anläggningstillgång'),
(86, '', 'Övriga materiella anläggningstillgångar', '', '', '1298', 'Ackumulerade nedskrivningar på övriga materiella anläggningstillgångar'),
(87, '', 'Övriga materiella anläggningstillgångar', '', '1', '1299', 'Ackumulerade avskrivningar på övriga materiella anläggningstillgångar'),
(88, '13', 'Finansiella anläggningstillgångar', '', '', '', ''),
(89, '131', 'Andelar i koncernföretag', '', '', '1310', 'Andelar i koncernföretag'),
(90, '', 'Andelar i koncernföretag', '', '', '1311', 'Aktier i noterade svenska koncernföretag'),
(91, '', 'Andelar i koncernföretag', '', '', '1312', 'Aktier i onoterade svenska koncernföretag'),
(92, '', 'Andelar i koncernföretag', '', '', '1313', 'Aktier i noterade utländska koncernföretag'),
(93, '', 'Andelar i koncernföretag', '', '', '1314', 'Aktier i onoterade utländska koncernföretag'),
(94, '', 'Andelar i koncernföretag', '', '', '1316', 'Andra andelar i svenska koncernföretag'),
(95, '', 'Andelar i koncernföretag', '', '', '1317', 'Andra andelar i utländska koncernförertag'),
(96, '', 'Andelar i koncernföretag', '', '', '1318', 'Ackumulerade nedskrivningar av andelar i koncernföretag'),
(97, '132', 'Långfristiga fordringar hos koncernföretag', '', '', '1320', 'Långfristiga fordringar hos koncernföretag'),
(98, '', 'Långfristiga fordringar hos koncernföretag', '', '', '1321', 'Långfristiga fordringar hos moderföretag'),
(99, '', 'Långfristiga fordringar hos koncernföretag', '', '', '1322', 'Långfristiga fordringar hos dotterföretag'),
(100, '', 'Långfristiga fordringar hos koncernföretag', '', '', '1323', 'Långfristiga fordringar hos andra koncernföretag'),
(101, '', 'Långfristiga fordringar hos koncernföretag', '', '', '1328', 'Ackumulerade nedskrivningar av långfristiga fordringar hos koncernföretag'),
(102, '133', 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1330', 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(103, '', 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1331', 'Andelar i intresseföretag'),
(104, '', 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1332', 'Ackumulerade nedskrivningar av andelar i intresseföretag'),
(105, '', 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1333', 'Andelar i gemensamt styrda företag'),
(106, '', 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1334', 'Ackumulerade nedskrivningar av andelar i gemensamt styrda företag'),
(107, '', 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1336', 'Andelar i övriga företag som det finns ett ägarintresse i'),
(108, '', 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1337', 'Ackumulerade nedskrivningar av andelar i övriga företag som det finns ett ägarintresse i'),
(109, '', 'Andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1338', 'Ackumulerade nedskrivningar av andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(110, '134', 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1340', 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(111, '', 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1341', 'Långfristiga fordringar hos intresseföretag'),
(112, '', 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1342', 'Ackumulerade nedskrivningar av långfristiga fordringar hos intresseföretag'),
(113, '', 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1343', 'Långfristiga fordringar hos gemensamt styrda företag'),
(114, '', 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1344', 'Ackumulerade nedskrivningar av långfristiga fordringar hos gemensamt styrda företag'),
(115, '', 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1346', 'Långfristiga fordringar hos övriga företag som det finns ett ägarintresse i'),
(116, '', 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1347', 'Ackumulerade nedskrivningar av långfristiga fordringar hos övriga företag som det finns ett ägarintresse i'),
(117, '', 'Långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1348', 'Ackumulerade nedskrivningar av långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(118, '135', 'Andelar och värdepapper i andra företag', '', '1', '1350', 'Andelar och värdepapper i andra företag'),
(119, '', 'Andelar och värdepapper i andra företag', '', '', '1351', 'Andelar i noterade företag'),
(120, '', 'Andelar och värdepapper i andra företag', '', '', '1352', 'Andra andelar'),
(121, '', 'Andelar och värdepapper i andra företag', '', '', '1353', 'Andelar i bostadsrättsföreningar'),
(122, '', 'Andelar och värdepapper i andra företag', '', '', '1354', 'Obligationer'),
(123, '', 'Andelar och värdepapper i andra företag', '', '', '1356', 'Andelar i ekonomiska föreningar, övriga företag'),
(124, '', 'Andelar och värdepapper i andra företag', '', '', '1357', 'Andelar i handelsbolag, andra företag'),
(125, '', 'Andelar och värdepapper i andra företag', '', '', '1358', 'Ackumulerade nedskrivningar av andra andelar och värdepapper'),
(126, '136', 'Lån till delägare eller närstående, långfristig del', '', '', '1360', 'Lån till delägare eller närstående, långfristig del'),
(127, '', 'Lån till delägare eller närstående, långfristig del', '', '', '1369', 'Ackumulerade nedskrivningar av lån till delägare eller närstående, långfristig del'),
(128, '137', 'Uppskjuten skattefordran', '1', '', '1370', 'Uppskjuten skattefordran'),
(129, '138', 'Andra långfristiga fordringar', '', '1', '1380', 'Andra långfristiga fordringar'),
(130, '', 'Andra långfristiga fordringar', '', '', '1381', 'Långfristiga reversfordringar'),
(131, '', 'Andra långfristiga fordringar', '', '', '1382', 'Långfristiga fordringar hos anställda'),
(132, '', 'Andra långfristiga fordringar', '', '', '1383', 'Lämnade depositioner, långfristiga'),
(133, '', 'Andra långfristiga fordringar', '', '', '1384', 'Derivat'),
(134, '', 'Andra långfristiga fordringar', '', '', '1385', 'Kapitalförsäkring'),
(135, '', 'Andra långfristiga fordringar', '', '', '1387', 'Långfristiga kontraktsfordringar'),
(136, '', 'Andra långfristiga fordringar', '', '', '1388', 'Långfristiga kundfordringar'),
(137, '', 'Andra långfristiga fordringar', '', '', '1389', 'Ackumulerade nedskrivningar av andra långfristiga fordringar'),
(138, '14', 'Lager, produkter i arbete och pågående arbeten', '', '', '', ''),
(139, '141', 'Lager av råvaror', '', '1', '1410', 'Lager av råvaror'),
(140, '', 'Lager av råvaror', '', '1', '1419', 'Förändring av lager av råvaror'),
(141, '142', 'Lager av tillsatsmaterial och förnödenheter', '', '', '1420', 'Lager av tillsatsmaterial och förnödenheter'),
(142, '', 'Lager av tillsatsmaterial och förnödenheter', '', '', '1429', 'Förändring av lager av tillsatsmaterial och förnödenheter'),
(143, '144', 'Produkter i arbete', '', '1', '1440', 'Produkter i arbete'),
(144, '', 'Produkter i arbete', '', '1', '1449', 'Förändring av produkter i arbete'),
(145, '145', 'Lager av färdiga varor', '', '1', '1450', 'Lager av färdiga varor'),
(146, '', 'Lager av färdiga varor', '', '1', '1459', 'Förändring av lager av färdiga varor'),
(147, '146', 'Lager av handelsvaror', '', '1', '1460', 'Lager av handelsvaror'),
(148, '', 'Lager av handelsvaror', '', '', '1465', 'Lager av varor VMB'),
(149, '', 'Lager av handelsvaror', '', '', '1466', 'Nedskrivning av varor VMB'),
(150, '', 'Lager av handelsvaror', '', '', '1467', 'Lager av varor VMB förenklad'),
(151, '', 'Lager av handelsvaror', '', '1', '1469', 'Förändring av lager av handelsvaror'),
(152, '147', 'Pågående arbeten', '', '1', '1470', 'Pågående arbeten'),
(153, '', 'Pågående arbeten', '', '', '1471', 'Pågående arbeten, nedlagda kostnader'),
(154, '', 'Pågående arbeten', '', '', '1478', 'Pågående arbeten, fakturering'),
(155, '', 'Pågående arbeten', '', '1', '1479', 'Förändring av pågående arbeten'),
(156, '148', 'Förskott för varor och tjänster', '', '1', '1480', 'Förskott för varor och tjänster'),
(157, '', 'Förskott för varor och tjänster', '', '', '1481', 'Remburser'),
(158, '', 'Förskott för varor och tjänster', '', '', '1489', 'Övriga förskott till leverantörer'),
(159, '149', 'Övriga lagertillgångar', '', '1', '1490', 'Övriga lagertillgångar'),
(160, '', 'Övriga lagertillgångar', '', '', '1491', 'Lager av värdepapper'),
(161, '', 'Övriga lagertillgångar', '', '', '1492', 'Lager av fastigheter'),
(162, '', 'Övriga lagertillgångar', '', '', '1493', 'Djur som klassificeras som omsättningstillgång'),
(163, '15', 'Kundfordringar', '', '', '', ''),
(164, '151', 'Kundfordringar', '', '1', '1510', 'Kundfordringar'),
(165, '', 'Kundfordringar', '', '', '1511', 'Kundfordringar'),
(166, '', 'Kundfordringar', '', '', '1512', 'Belånade kundfordringar (factoring)'),
(167, '', 'Kundfordringar', '', '1', '1513', 'Kundfordringar – delad faktura'),
(168, '', 'Kundfordringar', '', '', '1516', 'Tvistiga kundfordringar'),
(169, '', 'Kundfordringar', '1', '', '1518', 'Ej reskontraförda kundfordringar'),
(170, '', 'Kundfordringar', '', '1', '1519', 'Nedskrivning av kundfordringar'),
(171, '152', 'Växelfordringar', '', '', '1520', 'Växelfordringar'),
(172, '', 'Växelfordringar', '', '', '1525', 'Osäkra växelfordringar'),
(173, '', 'Växelfordringar', '', '', '1529', 'Nedskrivning av växelfordringar'),
(174, '153', 'Kontraktsfordringar', '', '', '1530', 'Kontraktsfordringar'),
(175, '', 'Kontraktsfordringar', '', '', '1531', 'Kontraktsfordringar'),
(176, '', 'Kontraktsfordringar', '', '', '1532', 'Belånade kontraktsfordringar'),
(177, '', 'Kontraktsfordringar', '', '', '1536', 'Tvistiga kontraktsfordringar'),
(178, '', 'Kontraktsfordringar', '', '', '1539', 'Nedskrivning av kontraktsfordringar'),
(179, '155', 'Konsignationsfordringar', '', '', '1550', 'Konsignationsfordringar'),
(180, '156', 'Kundfordringar hos koncernföretag', '', '', '1560', 'Kundfordringar hos koncernföretag'),
(181, '', 'Kundfordringar hos koncernföretag', '', '', '1561', 'Kundfordringar hos moderföretag'),
(182, '', 'Kundfordringar hos koncernföretag', '', '', '1562', 'Kundfordringar hos dotterföretag'),
(183, '', 'Kundfordringar hos koncernföretag', '', '', '1563', 'Kundfordringar hos andra koncernföretag'),
(184, '', 'Kundfordringar hos koncernföretag', '', '', '1568', 'Ej reskontraförda kundfordringar hos koncernföretag'),
(185, '', 'Kundfordringar hos koncernföretag', '', '', '1569', 'Nedskrivning av kundfordringar hos koncernföretag'),
(186, '157', 'Kundfordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1570', 'Kundfordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(187, '', 'Kundfordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1571', 'Kundfordringar hos intresseföretag'),
(188, '', 'Kundfordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1572', 'Kundfordringar hos gemensamt styrda företag'),
(189, '', 'Kundfordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1573', 'Kundfordringar hos övriga företag som det finns ett ägarintresse i'),
(190, '158', 'Fordringar för kontokort och kuponger', '', '1', '1580', 'Fordringar för kontokort och kuponger'),
(191, '16', 'Övriga kortfristiga fordringar', '', '', '', ''),
(192, '161', 'Kortfristiga fordringar hos anställda', '', '1', '1610', 'Kortfristiga fordringar hos anställda'),
(193, '', 'Kortfristiga fordringar hos anställda', '', '', '1611', 'Reseförskott'),
(194, '', 'Kortfristiga fordringar hos anställda', '', '', '1612', 'Kassaförskott'),
(195, '', 'Kortfristiga fordringar hos anställda', '', '', '1613', 'Övriga förskott'),
(196, '', 'Kortfristiga fordringar hos anställda', '', '', '1614', 'Tillfälliga lån till anställda'),
(197, '', 'Kortfristiga fordringar hos anställda', '', '', '1619', 'Övriga fordringar hos anställda'),
(198, '162', 'Upparbetad men ej fakturerad intäkt', '', '', '1620', 'Upparbetad men ej fakturerad intäkt'),
(199, '163', 'Avräkning för skatter och avgifter (skattekonto)', '', '1', '1630', 'Avräkning för skatter och avgifter (skattekonto)'),
(200, '164', 'Skattefordringar', '', '1', '1640', 'Skattefordringar'),
(201, '165', 'Momsfordran', '', '1', '1650', 'Momsfordran'),
(202, '166', 'Kortfristiga fordringar hos koncernföretag', '', '', '1660', 'Kortfristiga fordringar hos koncernföretag'),
(203, '', 'Kortfristiga fordringar hos koncernföretag', '', '', '1661', 'Kortfristiga fordringar hos moderföretag'),
(204, '', 'Kortfristiga fordringar hos koncernföretag', '', '', '1662', 'Kortfristiga fordringar hos dotterföretag'),
(205, '', 'Kortfristiga fordringar hos koncernföretag', '', '', '1663', 'Kortfristiga fordringar hos andra koncernföretag'),
(206, '167', 'Kortfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1670', 'Kortfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(207, '', 'Kortfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1671', 'Kortfristiga fordringar hos intresseföretag'),
(208, '', 'Kortfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1672', 'Kortfristiga fordringar hos gemensamt styrda företag'),
(209, '', 'Kortfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '1673', 'Kortfristiga fordringar hos övriga företag som det finns ett ägarintresse i'),
(210, '168', 'Andra kortfristiga fordringar', '', '1', '1680', 'Andra kortfristiga fordringar'),
(211, '', 'Andra kortfristiga fordringar', '', '', '1681', 'Utlägg för kunder'),
(212, '', 'Andra kortfristiga fordringar', '', '', '1682', 'Kortfristiga lånefordringar'),
(213, '', 'Andra kortfristiga fordringar', '', '', '1683', 'Derivat'),
(214, '', 'Andra kortfristiga fordringar', '', '', '1684', 'Kortfristiga fordringar hos leverantörer'),
(215, '', 'Andra kortfristiga fordringar', '', '', '1685', 'Kortfristiga fordringar hos delägare eller närstående'),
(216, '', 'Andra kortfristiga fordringar', '', '', '1687', 'Kortfristig del av långfristiga fordringar'),
(217, '', 'Andra kortfristiga fordringar', '', '', '1688', 'Fordran arbetsmarknadsförsäkringar'),
(218, '', 'Andra kortfristiga fordringar', '', '', '1689', 'Övriga kortfristiga fordringar'),
(219, '169', 'Fordringar för tecknat men ej inbetalt aktiekapital', '', '', '1690', 'Fordringar för tecknat men ej inbetalt aktiekapital'),
(220, '17', 'Förutbetalda kostnader och upplupna intäkter', '', '', '', ''),
(221, '171', 'Förutbetalda hyreskostnader', '', '1', '1710', 'Förutbetalda hyreskostnader'),
(222, '172', 'Förutbetalda leasingavgifter', '', '1', '1720', 'Förutbetalda leasingavgifter'),
(223, '173', 'Förutbetalda försäkringspremier', '', '1', '1730', 'Förutbetalda försäkringspremier'),
(224, '174', 'Förutbetalda räntekostnader', '', '1', '1740', 'Förutbetalda räntekostnader'),
(225, '175', 'Upplupna hyresintäkter', '', '1', '1750', 'Upplupna hyresintäkter'),
(226, '176', 'Upplupna ränteintäkter', '', '1', '1760', 'Upplupna ränteintäkter'),
(227, '177', 'Tillgångar av kostnadsnatur', '', '', '1770', 'Tillgångar av kostnadsnatur'),
(228, '178', 'Upplupna avtalsintäkter', '', '', '1780', 'Upplupna avtalsintäkter'),
(229, '179', 'Övriga förutbetalda kostnader och upplupna intäkter', '', '1', '1790', 'Övriga förutbetalda kostnader och upplupna intäkter'),
(230, '18', 'Kortfristiga placeringar', '', '', '', ''),
(231, '181', 'Andelar i börsnoterade företag', '', '1', '1810', 'Andelar i börsnoterade företag'),
(232, '182', 'Obligationer', '', '', '1820', 'Obligationer'),
(233, '183', 'Konvertibla skuldebrev', '', '', '1830', 'Konvertibla skuldebrev'),
(234, '186', 'Andelar i koncernföretag, kortfristigt', '', '', '1860', 'Andelar i koncernföretag, kortfristigt'),
(235, '188', 'Andra kortfristiga placeringar', '', '1', '1880', 'Andra kortfristiga placeringar'),
(236, '', 'Andra kortfristiga placeringar', '', '', '1886', 'Derivat'),
(237, '', 'Andra kortfristiga placeringar', '', '', '1889', 'Andelar i övriga företag'),
(238, '189', 'Nedskrivning av kortfristiga placeringar', '', '1', '1890', 'Nedskrivning av kortfristiga placeringar'),
(239, '19', 'Kassa och bank', '', '', '', ''),
(240, '191', 'Kassa', '', '1', '1910', 'Kassa'),
(241, '', 'Kassa', '', '', '1911', 'Huvudkassa'),
(242, '', 'Kassa', '', '', '1912', 'Kassa 2'),
(243, '', 'Kassa', '', '', '1913', 'Kassa 3'),
(244, '192', 'PlusGiro', '', '1', '1920', 'PlusGiro'),
(245, '193', 'Företagskonto/checkkonto/affärskonto', '', '1', '1930', 'Företagskonto/checkkonto/affärskonto'),
(246, '194', 'Övriga bankkonton', '', '1', '1940', 'Övriga bankkonton'),
(247, '195', 'Bankcertifikat', '', '', '1950', 'Bankcertifikat'),
(248, '196', 'Koncernkonto moderföretag', '', '', '1960', 'Koncernkonto moderföretag'),
(249, '197', 'Särskilda bankkonton', '', '', '1970', 'Särskilda bankkonton'),
(250, '', 'Särskilda bankkonton', '', '', '1972', 'Upphovsmannakonto'),
(251, '', 'Särskilda bankkonton', '', '', '1973', 'Skogskonto'),
(252, '', 'Särskilda bankkonton', '', '', '1974', 'Spärrade bankmedel'),
(253, '', 'Särskilda bankkonton', '', '', '1979', 'Övriga särskilda bankkonton'),
(254, '198', 'Valutakonton', '', '', '1980', 'Valutakonton'),
(255, '199', 'Redovisningsmedel', '', '', '1990', 'Redovisningsmedel'),
(256, '2', 'Eget kapital och skulder', '', '', '', ''),
(257, '20', 'Eget kapital', '', '', '', ''),
(258, '201', 'Eget kapital (enskild firma)', '', '1', '2010', 'Eget kapital'),
(259, '', 'Eget kapital (enskild firma)', '', '1', '2011', 'Egna varuuttag'),
(260, '', 'Eget kapital (enskild firma)', '', '1', '2013', 'Övriga egna uttag'),
(261, '', 'Eget kapital (enskild firma)', '', '1', '2017', 'Årets kapitaltillskott'),
(262, '', 'Eget kapital (enskild firma)', '', '1', '2018', 'Övriga egna insättningar'),
(263, '', 'Eget kapital (enskild firma)', '', '1', '2019', 'Årets resultat'),
(264, '201', 'Eget kapital, delägare 1', '', '1', '2010', 'Eget kapital'),
(265, '', 'Eget kapital, delägare 1', '', '1', '2011', 'Egna varuuttag'),
(266, '', 'Eget kapital, delägare 1', '', '1', '2013', 'Övriga egna uttag'),
(267, '', 'Eget kapital, delägare 1', '', '1', '2017', 'Årets kapitaltillskott'),
(268, '', 'Eget kapital, delägare 1', '', '1', '2018', 'Övriga egna insättningar'),
(269, '', 'Eget kapital, delägare 1', '', '1', '2019', 'Årets resultat, delägare 1'),
(270, '202', 'Eget kapital, delägare 2', '', '1', '2020', 'Eget kapital'),
(271, '', 'Eget kapital, delägare 2', '', '1', '2021', 'Egna varuuttag'),
(272, '', 'Eget kapital, delägare 2', '', '1', '2023', 'Övriga egna uttag'),
(273, '', 'Eget kapital, delägare 2', '', '1', '2027', 'Årets kapitaltillskott'),
(274, '', 'Eget kapital, delägare 2', '', '1', '2028', 'Övriga egna insättningar'),
(275, '', 'Eget kapital, delägare 2', '', '1', '2029', 'Årets resultat, delägare 2'),
(276, '203', 'Eget kapital, delägare 3', '', '1', '2030', 'Eget kapital'),
(277, '', 'Eget kapital, delägare 3', '', '1', '2031', 'Egna varuuttag'),
(278, '', 'Eget kapital, delägare 3', '', '1', '2033', 'Övriga egna uttag'),
(279, '', 'Eget kapital, delägare 3', '', '1', '2037', 'Årets kapitaltillskott'),
(280, '', 'Eget kapital, delägare 3', '', '1', '2038', 'Övriga egna insättningar'),
(281, '', 'Eget kapital, delägare 3', '', '1', '2039', 'Årets resultat, delägare 3'),
(282, '204', 'Eget kapital, delägare 4', '', '1', '2040', 'Eget kapital'),
(283, '', 'Eget kapital, delägare 4', '', '1', '2041', 'Egna varuuttag'),
(284, '', 'Eget kapital, delägare 4', '', '1', '2043', 'Övriga egna uttag'),
(285, '', 'Eget kapital, delägare 4', '', '1', '2047', 'Årets kapitaltillskott'),
(286, '', 'Eget kapital, delägare 4', '', '1', '2048', 'Övriga egna insättningar'),
(287, '', 'Eget kapital, delägare 4', '', '1', '2049', 'Årets resultat, delägare 4'),
(288, '205', 'Avsättning till expansionsfond', '', '', '2050', 'Avsättning till expansionsfond'),
(289, '206', 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', '', '1', '2060', 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund'),
(290, '', 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', '', '', '2061', 'Kapital/stiftelsekapital/grundkapital'),
(291, '', 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', '', '', '2064', 'Ackumulerat realisationsresultat'),
(292, '', 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', '', '', '2065', 'Fond för verkligt värde'),
(293, '', 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', '', '', '2066', 'Värdesäkringsfond'),
(294, '', 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', '', '', '2067', 'Balanserat överskott eller underskott'),
(295, '', 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', '', '', '2068', 'Överskott eller underskott från föregående år'),
(296, '', 'Eget kapital i ideella föreningar, stiftelser och registrerade trossamfund', '', '', '2069', 'Årets resultat'),
(297, '207', 'Ändamålsbestämda medel', '', '1', '2070', 'Ändamålsbestämda medel'),
(298, '', 'Ändamålsbestämda medel', '', '', '2071', 'Ändamål 1'),
(299, '', 'Ändamålsbestämda medel', '', '', '2072', 'Ändamål 2'),
(300, '208', 'Bundet eget kapital', '', '', '2080', 'Bundet eget kapital'),
(301, '', 'Bundet eget kapital', '', '1', '2081', 'Aktiekapital'),
(302, '', 'Bundet eget kapital', '', '', '2082', 'Ej registrerat aktiekapital'),
(303, '', 'Bundet eget kapital', '', '1', '2083', 'Medlemsinsatser'),
(304, '', 'Bundet eget kapital', '', '', '2084', 'Förlagsinsatser'),
(305, '', 'Bundet eget kapital', '', '', '2085', 'Uppskrivningsfond'),
(306, '', 'Bundet eget kapital', '', '1', '2086', 'Reservfond'),
(307, '', 'Bundet eget kapital', '', '', '2087', 'Insatsemission'),
(308, '', 'Bundet eget kapital', '', '', '2087', 'Bunden överkursfond'),
(309, '', 'Bundet eget kapital', '', '', '2088', 'Fond för yttre underhåll'),
(310, '', 'Bundet eget kapital', '1', '', '2089', 'Fond för utvecklingsutgifter'),
(311, '209', 'Fritt eget kapital', '', '1', '2090', 'Fritt eget kapital'),
(312, '', 'Fritt eget kapital', '', '1', '2091', 'Balanserad vinst eller förlust'),
(313, '', 'Fritt eget kapital', '1', '', '2092', 'Mottagna/lämnade koncernbidrag'),
(314, '', 'Fritt eget kapital', '', '', '2093', 'Erhållna aktieägartillskott'),
(315, '', 'Fritt eget kapital', '', '', '2094', 'Egna aktier'),
(316, '', 'Fritt eget kapital', '', '', '2095', 'Fusionsresultat'),
(317, '', 'Fritt eget kapital', '1', '', '2096', 'Fond för verkligt värde'),
(318, '', 'Fritt eget kapital', '', '', '2097', 'Fri överkursfond'),
(319, '', 'Fritt eget kapital', '', '1', '2098', 'Vinst eller förlust från föregående år'),
(320, '', 'Fritt eget kapital', '', '1', '2099', 'Årets resultat'),
(321, '21', 'Obeskattade reserver', '', '', '', ''),
(322, '211', 'Periodiseringsfonder', '', '', '2110', 'Periodiseringsfonder'),
(323, '212', 'Periodiseringsfond 2020', '', '1', '2120', 'Periodiseringsfond 2020'),
(324, '', 'Periodiseringsfond 2021', '', '1', '2121', 'Periodiseringsfond 2021'),
(325, '', 'Periodiseringsfond 2022', '', '1', '2122', 'Periodiseringsfond 2022'),
(326, '', 'Periodiseringsfond 2023', '', '1', '2123', 'Periodiseringsfond 2023'),
(327, '', 'Periodiseringsfond 2024', '', '1', '2124', 'Periodiseringsfond 2024'),
(328, '', 'Periodiseringsfond 2025', '', '1', '2125', 'Periodiseringsfond 2025'),
(329, '', 'Periodiseringsfond 2026', '', '1', '2126', 'Periodiseringsfond 2026'),
(330, '', 'Periodiseringsfond 2018', '', '1', '2128', 'Periodiseringsfond 2018'),
(331, '', '2019', '', '1', '2129', 'Periodiseringsfond 2019'),
(332, '213', 'Periodiseringsfond 2020 – nr 2', '', '', '2130', 'Periodiseringsfond 2020 – nr 2'),
(333, '', 'Periodiseringsfond 2021 – nr 2', '', '', '2131', 'Periodiseringsfond 2021 – nr 2'),
(334, '', 'Periodiseringsfond 2022 – nr 2', '', '', '2132', 'Periodiseringsfond 2022 – nr 2'),
(335, '', 'Periodiseringsfond 2023 – nr 2', '', '', '2133', 'Periodiseringsfond 2023 – nr 2'),
(336, '', 'Periodiseringsfond 2024 – nr 2', '', '', '2134', 'Periodiseringsfond 2024 – nr 2'),
(337, '', 'Periodiseringsfond 2025 - nr 2', '', '', '2135', 'Periodiseringsfond 2025 - nr 2'),
(338, '', 'Periodiseringsfond 2026 - nr 2', '', '', '2136', 'Periodiseringsfond 2026 - nr 2'),
(339, '', 'Periodiseringsfond 2018 – nr 2', '', '', '2138', 'Periodiseringsfond 2018 – nr 2'),
(340, '', 'Periodiseringsfond 2019 – nr 2', '', '', '2139', 'Periodiseringsfond 2019 – nr 2'),
(341, '215', 'Ackumulerade överavskrivningar', '', '1', '2150', 'Ackumulerade överavskrivningar'),
(342, '', 'Ackumulerade överavskrivningar', '', '', '2151', 'Ackumulerade överavskrivningar på immateriella anläggningstillgångar'),
(343, '', 'Ackumulerade överavskrivningar', '', '', '2152', 'Ackumulerade överavskrivningar på byggnader och markanläggningar'),
(344, '', 'Ackumulerade överavskrivningar', '', '', '2153', 'Ackumulerade överavskrivningar på maskiner och inventarier'),
(345, '216', 'Ersättningsfond', '', '', '2160', 'Ersättningsfond'),
(346, '', 'Ersättningsfond', '', '', '2161', 'Ersättningsfond maskiner och inventarier'),
(347, '', 'Ersättningsfond', '', '', '2162', 'Ersättningsfond byggnader och markanläggningar'),
(348, '', 'Ersättningsfond', '', '', '2164', 'Ersättningsfond för djurlager i jordbruk och renskötsel'),
(349, '219', 'Övriga obeskattade reserver', '', '', '2190', 'Övriga obeskattade reserver'),
(350, '', 'Övriga obeskattade reserver', '', '', '2196', 'Lagerreserv'),
(351, '', 'Övriga obeskattade reserver', '', '', '2199', 'Övriga obeskattade reserver'),
(352, '22', 'Avsättningar', '', '', '', ''),
(353, '221', 'Avsättningar för pensioner enligt tryggandelagen', '', '1', '2210', 'Avsättningar för pensioner enligt tryggandelagen'),
(354, '222', 'Avsättningar för garantier', '', '1', '2220', 'Avsättningar för garantier'),
(355, '223', 'Övriga avsättningar för pensioner och liknande förpliktelser', '', '', '2230', 'Övriga avsättningar för pensioner och liknande förpliktelser'),
(356, '224', 'Avsättningar för uppskjutna skatter', '1', '', '2240', 'Avsättningar för uppskjutna skatter'),
(357, '225', 'Övriga avsättningar för skatter', '', '', '2250', 'Övriga avsättningar för skatter'),
(358, '', 'Övriga avsättningar för skatter', '', '', '2252', 'Avsättningar för tvistiga skatter'),
(359, '', 'Övriga avsättningar för skatter', '', '', '2253', 'Avsättningar särskild löneskatt, deklarationspost'),
(360, '229', 'Övriga avsättningar', '', '1', '2290', 'Övriga avsättningar'),
(361, '23', 'Långfristiga skulder', '', '', '', ''),
(362, '231', 'Obligations- och förlagslån', '', '', '2310', 'Obligations- och förlagslån'),
(363, '232', 'Konvertibla lån och liknande', '', '', '2320', 'Konvertibla lån och liknande'),
(364, '', 'Konvertibla lån och liknande', '', '', '2321', 'Konvertibla lån'),
(365, '', 'Konvertibla lån och liknande', '', '', '2322', 'Lån förenade med optionsrätt'),
(366, '', 'Konvertibla lån och liknande', '', '', '2323', 'Vinstandelslån'),
(367, '', 'Konvertibla lån och liknande', '', '', '2324', 'Kapitalandelslån'),
(368, '233', 'Checkräkningskredit', '', '1', '2330', 'Checkräkningskredit'),
(369, '', 'Checkräkningskredit', '', '', '2331', 'Checkräkningskredit 1'),
(370, '', 'Checkräkningskredit', '', '', '2332', 'Checkräkningskredit 2'),
(371, '234', 'Byggnadskreditiv', '', '', '2340', 'Byggnadskreditiv'),
(372, '235', 'Andra långfristiga skulder till kreditinstitut', '', '1', '2350', 'Andra långfristiga skulder till kreditinstitut'),
(373, '', 'Andra långfristiga skulder till kreditinstitut', '', '', '2351', 'Fastighetslån, långfristig del'),
(374, '', 'Andra långfristiga skulder till kreditinstitut', '', '', '2355', 'Långfristiga lån i utländsk valuta från kreditinstitut'),
(375, '', 'Andra långfristiga skulder till kreditinstitut', '', '', '2359', 'Övriga långfristiga lån från kreditinstitut'),
(376, '236', 'Långfristiga skulder till koncernföretag', '', '', '2360', 'Långfristiga skulder till koncernföretag'),
(377, '', 'Långfristiga skulder till koncernföretag', '', '', '2361', 'Långfristiga skulder till moderföretag'),
(378, '', 'Långfristiga skulder till koncernföretag', '', '', '2362', 'Långfristiga skulder till dotterföretag'),
(379, '', 'Långfristiga skulder till koncernföretag', '', '', '2363', 'Långfristiga skulder till andra koncernföretag'),
(380, '237', 'Långfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '2370', 'Långfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(381, '', 'Långfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '2371', 'Långfristiga skulder till intresseföretag'),
(382, '', 'Långfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '2372', 'Långfristiga skulder till gemensamt styrda företag'),
(383, '', 'Långfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '2373', 'Långfristiga skulder till övriga företag som det finns ett ägarintresse i'),
(384, '239', 'Övriga långfristiga skulder', '', '1', '2390', 'Övriga långfristiga skulder'),
(385, '', 'Övriga långfristiga skulder', '', '', '2391', 'Avbetalningskontrakt, långfristig del'),
(386, '', 'Övriga långfristiga skulder', '', '', '2392', 'Villkorliga långfristiga skulder'),
(387, '', 'Övriga långfristiga skulder', '', '1', '2393', 'Lån från närstående personer, långfristig del'),
(388, '', 'Övriga långfristiga skulder', '', '', '2394', 'Långfristiga leverantörskrediter'),
(389, '', 'Övriga långfristiga skulder', '', '', '2395', 'Andra långfristiga lån i utländsk valuta'),
(390, '', 'Övriga långfristiga skulder', '', '', '2396', 'Derivat'),
(391, '', 'Övriga långfristiga skulder', '', '', '2397', 'Mottagna depositioner, långfristiga'),
(392, '', 'Övriga långfristiga skulder', '', '', '2399', 'Övriga långfristiga skulder'),
(393, '24', 'Kortfristiga skulder till kreditinstitut, kunder och leverantörer', '', '', '', ''),
(394, '241', 'Andra kortfristiga låneskulder till kreditinstitut', '', '1', '2410', 'Andra kortfristiga låneskulder till kreditinstitut'),
(395, '', 'Andra kortfristiga låneskulder till kreditinstitut', '', '', '2411', 'Kortfristiga lån från kreditinstitut'),
(396, '', 'Andra kortfristiga låneskulder till kreditinstitut', '', '', '2412', 'Byggnadskreditiv, kortfristig del'),
(397, '', 'Andra kortfristiga låneskulder till kreditinstitut', '', '', '2417', 'Kortfristig del av långfristiga skulder till kreditinstitut'),
(398, '', 'Andra kortfristiga låneskulder till kreditinstitut', '', '', '2419', 'Övriga kortfristiga skulder till kreditinstitut'),
(399, '242', 'Förskott från kunder', '', '1', '2420', 'Förskott från kunder'),
(400, '', 'Förskott från kunder', '', '', '2421', 'Ej inlösta presentkort'),
(401, '', 'Förskott från kunder', '', '', '2429', 'Övriga förskott från kunder'),
(402, '243', 'Pågående arbeten', '', '', '2430', 'Pågående arbeten'),
(403, '', 'Pågående arbeten', '', '', '2431', 'Pågående arbeten, fakturering'),
(404, '', 'Pågående arbeten', '', '', '2438', 'Pågående arbeten, nedlagda kostnader'),
(405, '', 'Pågående arbeten', '', '', '2439', 'Beräknad förändring av pågående arbeten'),
(406, '244', 'Leverantörsskulder', '', '1', '2440', 'Leverantörsskulder'),
(407, '', 'Leverantörsskulder', '', '', '2441', 'Leverantörsskulder'),
(408, '', 'Leverantörsskulder', '', '', '2443', 'Konsignationsskulder'),
(409, '', 'Leverantörsskulder', '', '', '2445', 'Tvistiga leverantörsskulder'),
(410, '', 'Leverantörsskulder', '1', '', '2448', 'Ej reskontraförda leverantörsskulder'),
(411, '245', 'Fakturerad men ej upparbetad intäkt', '', '', '2450', 'Fakturerad men ej upparbetad intäkt'),
(412, '246', 'Leverantörsskulder till koncernföretag', '', '', '2460', 'Leverantörsskulder till koncernföretag'),
(413, '', 'Leverantörsskulder till koncernföretag', '', '', '2461', 'Leverantörsskulder till moderföretag'),
(414, '', 'Leverantörsskulder till koncernföretag', '', '', '2462', 'Leverantörsskulder till dotterföretag'),
(415, '', 'Leverantörsskulder till koncernföretag', '', '', '2463', 'Leverantörsskulder till andra koncernföretag'),
(416, '247', 'Leverantörsskulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '2470', 'Leverantörsskulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(417, '', 'Leverantörsskulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '2471', 'Leverantörsskulder till intresseföretag'),
(418, '', 'Leverantörsskulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '2472', 'Leverantörsskulder till gemensamt styrda företag'),
(419, '', 'Leverantörsskulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '2473', 'Leverantörsskulder till övriga företag som det finns ett ägarintresse i'),
(420, '248', 'Checkräkningskredit, kortfristig', '', '1', '2480', 'Checkräkningskredit, kortfristig'),
(421, '249', 'Övriga kortfristiga skulder till kreditinstitut, kunder och leverantörer', '', '1', '2490', 'Övriga kortfristiga skulder till kreditinstitut, kunder och leverantörer'),
(422, '', 'Övriga kortfristiga skulder till kreditinstitut, kunder och leverantörer', '', '', '2491', 'Avräkning spelarrangörer'),
(423, '', 'Övriga kortfristiga skulder till kreditinstitut, kunder och leverantörer', '', '', '2492', 'Växelskulder'),
(424, '', 'Övriga kortfristiga skulder till kreditinstitut, kunder och leverantörer', '', '', '2499', 'Andra övriga kortfristiga skulder'),
(425, '25', 'Skatteskulder', '', '', '', ''),
(426, '251', 'Skatteskulder', '', '1', '2510', 'Skatteskulder'),
(427, '', 'Skatteskulder', '', '', '2512', 'Beräknad inkomstskatt'),
(428, '', 'Skatteskulder', '', '', '2513', 'Beräknad fastighetsskatt/fastighetsavgift'),
(429, '', 'Skatteskulder', '', '', '2514', 'Beräknad särskild löneskatt på pensionskostnader'),
(430, '', 'Skatteskulder', '', '', '2515', 'Beräknad avkastningsskatt'),
(431, '', 'Skatteskulder', '', '', '2517', 'Beräknad utländsk skatt'),
(432, '', 'Skatteskulder', '', '', '2518', 'Betald F-skatt'),
(433, '26', 'Moms och punktskatter', '', '', '', ''),
(434, '261', 'Utgående moms, 25 %', '', '1', '2610', 'Utgående moms, 25 %'),
(435, '', 'Utgående moms, 25 %', '', '1', '2611', 'Utgående moms på försäljning inom Sverige, 25 %'),
(436, '', 'Utgående moms, 25 %', '', '1', '2612', 'Utgående moms på egna uttag, 25 %'),
(437, '', 'Utgående moms, 25 %', '', '1', '2613', 'Utgående moms för uthyrning, 25 %'),
(438, '', 'Utgående moms, 25 %', '', '1', '2614', 'Utgående moms, omvänd betalningsskyldighet, 25 %'),
(439, '', 'Utgående moms, 25 %', '', '1', '2615', 'Utgående moms import av varor, 25 %'),
(440, '', 'Utgående moms, 25 %', '', '1', '2616', 'Utgående moms VMB 25 %'),
(441, '', 'Utgående moms, 25 %', '', '', '2618', 'Vilande utgående moms, 25 %'),
(442, '262', 'Utgående moms, 12 %', '', '1', '2620', 'Utgående moms, 12 %'),
(443, '', 'Utgående moms, 12 %', '', '1', '2621', 'Utgående moms på försäljning inom Sverige, 12 %'),
(444, '', 'Utgående moms, 12 %', '', '1', '2622', 'Utgående moms på egna uttag, 12 %'),
(445, '', 'Utgående moms, 12 %', '', '1', '2623', 'Utgående moms för uthyrning, 12 %'),
(446, '', 'Utgående moms, 12 %', '', '1', '2624', 'Utgående moms, omvänd betalningsskyldighet, 12 %'),
(447, '', 'Utgående moms, 12 %', '', '1', '2625', 'Utgående moms import av varor, 12 %'),
(448, '', 'Utgående moms, 12 %', '', '1', '2626', 'Utgående moms VMB 12 %'),
(449, '', 'Utgående moms, 12 %', '', '', '2628', 'Vilande utgående moms, 12 %'),
(450, '263', 'Utgående moms, 6 %', '', '1', '2630', 'Utgående moms, 6 %'),
(451, '', 'Utgående moms, 6 %', '', '1', '2631', 'Utgående moms på försäljning inom Sverige, 6 %'),
(452, '', 'Utgående moms, 6 %', '', '1', '2632', 'Utgående moms på egna uttag, 6 %'),
(453, '', 'Utgående moms, 6 %', '', '1', '2633', 'Utgående moms för uthyrning, 6 %'),
(454, '', 'Utgående moms, 6 %', '', '1', '2634', 'Utgående moms, omvänd betalningsskyldighet, 6 %'),
(455, '', 'Utgående moms, 6 %', '', '1', '2635', 'Utgående moms import av varor, 6 %'),
(456, '', 'Utgående moms, 6 %', '', '1', '2636', 'Utgående moms VMB 6 %'),
(457, '', 'Utgående moms, 6 %', '', '', '2638', 'Vilande utgående moms, 6 %'),
(458, '264', 'Ingående moms', '', '1', '2640', 'Ingående moms'),
(459, '', 'Ingående moms', '', '1', '2641', 'Debiterad ingående moms'),
(460, '', 'Ingående moms', '', '1', '2642', 'Debiterad ingående moms i anslutning till frivillig betalningsskyldighet'),
(461, '', 'Ingående moms', '', '1', '2645', 'Beräknad ingående moms på förvärv från utlandet'),
(462, '', 'Ingående moms', '', '1', '2646', 'Ingående moms på uthyrning'),
(463, '', 'Ingående moms', '', '1', '2647', 'Ingående moms, omvänd betalningsskyldighet varor och tjänster i Sverige'),
(464, '', 'Ingående moms', '', '1', '2648', 'Vilande ingående moms'),
(465, '', 'Ingående moms', '', '1', '2649', 'Ingående moms, blandad verksamhet'),
(466, '265', 'Redovisningskonto för moms', '', '1', '2650', 'Redovisningskonto för moms'),
(467, '266', 'Punktskatter', '', '', '2660', 'Punktskatter'),
(468, '267', 'Utgående moms, OSS', '', '', '2670', 'Utgående moms på försäljning inom EU, OSS'),
(469, '27', 'Personalens skatter, avgifter och löneavdrag', '', '', '', ''),
(470, '271', 'Personalskatt', '', '1', '2710', 'Personalskatt'),
(471, '273', 'Lagstadgade sociala avgifter och särskild löneskatt', '', '1', '2730', 'Lagstadgade sociala avgifter och särskild löneskatt'),
(472, '', 'Lagstadgade sociala avgifter och särskild löneskatt', '', '', '2731', 'Avräkning lagstadgade sociala avgifter'),
(473, '', 'Lagstadgade sociala avgifter och särskild löneskatt', '', '', '2732', 'Avräkning särskild löneskatt'),
(474, '274', 'Avtalade sociala avgifter', '', '1', '2740', 'Avtalade sociala avgifter'),
(475, '275', 'Utmätning i lön m.m.', '', '', '2750', 'Utmätning i lön m.m.'),
(476, '276', 'Semestermedel', '', '', '2760', 'Semestermedel'),
(477, '', 'Semestermedel', '', '', '2761', 'Avräkning semesterlöner'),
(478, '', 'Semestermedel', '', '', '2762', 'Semesterlönekassa'),
(479, '279', 'Övriga löneavdrag', '', '1', '2790', 'Övriga löneavdrag'),
(480, '', 'Övriga löneavdrag', '', '', '2791', 'Personalens intressekonto'),
(481, '', 'Övriga löneavdrag', '', '', '2792', 'Lönsparande'),
(482, '', 'Övriga löneavdrag', '', '', '2793', 'Gruppförsäkringspremier'),
(483, '', 'Övriga löneavdrag', '', '', '2794', 'Fackföreningsavgifter'),
(484, '', 'Övriga löneavdrag', '', '', '2795', 'Mätnings- och granskningsarvoden'),
(485, '', 'Övriga löneavdrag', '', '', '2799', 'Övriga löneavdrag'),
(486, '28', 'Övriga kortfristiga skulder', '', '', '', ''),
(487, '281', 'Avräkning för factoring och belånade kontraktsfordringar', '', '', '2810', 'Avräkning för factoring och belånade kontraktsfordringar'),
(488, '', 'Avräkning för factoring och belånade kontraktsfordringar', '', '', '2811', 'Avräkning för factoring'),
(489, '', 'Avräkning för factoring och belånade kontraktsfordringar', '', '', '2812', 'Avräkning för belånade kontraktsfordringar'),
(490, '282', 'Kortfristiga skulder till anställda', '', '1', '2820', 'Kortfristiga skulder till anställda'),
(491, '', 'Kortfristiga skulder till anställda', '', '', '2821', 'Löneskulder'),
(492, '', 'Kortfristiga skulder till anställda', '', '', '2822', 'Reseräkningar'),
(493, '', 'Kortfristiga skulder till anställda', '', '', '2823', 'Tantiem, gratifikationer'),
(494, '', 'Kortfristiga skulder till anställda', '', '', '2829', 'Övriga kortfristiga skulder till anställda'),
(495, '283', 'Avräkning för annans räkning', '', '', '2830', 'Avräkning för annans räkning'),
(496, '284', 'Kortfristiga låneskulder', '', '1', '2840', 'Kortfristiga låneskulder'),
(497, '', 'Kortfristiga låneskulder', '', '', '2841', 'Kortfristig del av långfristiga skulder'),
(498, '', 'Kortfristiga låneskulder', '', '', '2849', 'Övriga kortfristiga låneskulder'),
(499, '285', 'Avräkning för skatter och avgifter (skattekonto)', '', '', '2850', 'Avräkning för skatter och avgifter (skattekonto)'),
(500, '', 'Avräkning för skatter och avgifter (skattekonto)', '', '', '2852', 'Anståndsbelopp för moms, arbetsgivaravgifter och personalskatt'),
(501, '286', 'Kortfristiga skulder till koncernföretag', '', '', '2860', 'Kortfristiga skulder till koncernföretag'),
(502, '', 'Kortfristiga skulder till koncernföretag', '', '', '2861', 'Kortfristiga skulder till moderföretag'),
(503, '', 'Kortfristiga skulder till koncernföretag', '', '', '2862', 'Kortfristiga skulder till dotterföretag'),
(504, '', 'Kortfristiga skulder till koncernföretag', '', '', '2863', 'Kortfristiga skulder till andra koncernföretag'),
(505, '287', 'Kortfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '2870', 'Kortfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i');
INSERT INTO `chart_of_accounts` (`id`, `main_account`, `main_account_description`, `no_k2`, `simple_account`, `sub_account`, `sub_account_description`) VALUES
(506, '', 'Kortfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '2871', 'Kortfristiga skulder till intresseföretag'),
(507, '', 'Kortfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '2872', 'Kortfristiga skulder till gemensamt styrda företag'),
(508, '', 'Kortfristiga skulder till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '2873', 'Kortfristiga skulder till övriga företag som det finns ett ägarintresse i'),
(509, '288', 'Skuld erhållna bidrag', '', '', '2880', 'Skuld erhållna bidrag'),
(510, '289', 'Övriga kortfristiga skulder', '', '1', '2890', 'Övriga kortfristiga skulder'),
(511, '', 'Övriga kortfristiga skulder', '', '', '2891', 'Skulder under indrivning'),
(512, '', 'Övriga kortfristiga skulder', '', '', '2892', 'Inre reparationsfond/underhållsfond'),
(513, '', 'Övriga kortfristiga skulder', '', '', '2893', 'Skulder till närstående personer, kortfristig del'),
(514, '', 'Övriga kortfristiga skulder', '', '', '2895', 'Derivat (kortfristiga skulder)'),
(515, '', 'Övriga kortfristiga skulder', '', '', '2897', 'Mottagna depositioner, kortfristiga'),
(516, '', 'Övriga kortfristiga skulder', '', '', '2898', 'Outtagen vinstutdelning'),
(517, '', 'Övriga kortfristiga skulder', '', '', '2899', 'Övriga kortfristiga skulder'),
(518, '29', 'Upplupna kostnader och förutbetalda intäkter', '', '', '', ''),
(519, '291', 'Upplupna löner', '', '1', '2910', 'Upplupna löner'),
(520, '', 'Upplupna löner', '', '', '2911', 'Löneskulder'),
(521, '', 'Upplupna löner', '', '', '2912', 'Ackordsöverskott'),
(522, '', 'Upplupna löner', '', '', '2919', 'Övriga upplupna löner'),
(523, '292', 'Upplupna semesterlöner', '', '1', '2920', 'Upplupna semesterlöner'),
(524, '293', 'Upplupna pensionskostnader', '', '', '2930', 'Upplupna pensionskostnader'),
(525, '', 'Upplupna pensionskostnader', '', '', '2931', 'Upplupna pensionsutbetalningar'),
(526, '294', 'Upplupna lagstadgade sociala och andra avgifter', '', '1', '2940', 'Upplupna lagstadgade sociala och andra avgifter'),
(527, '', 'Upplupna lagstadgade sociala och andra avgifter', '', '', '2941', 'Beräknade upplupna lagstadgade sociala avgifter'),
(528, '', 'Upplupna lagstadgade sociala och andra avgifter', '', '', '2942', 'Beräknad upplupen särskild löneskatt'),
(529, '', 'Upplupna lagstadgade sociala och andra avgifter', '', '', '2943', 'Beräknad upplupen särskild löneskatt på pensionskostnader, deklarationspost'),
(530, '', 'Upplupna lagstadgade sociala och andra avgifter', '', '', '2944', 'Beräknad upplupen avkastningsskatt på pensionskostnader'),
(531, '295', 'Upplupna avtalade sociala avgifter', '', '1', '2950', 'Upplupna avtalade sociala avgifter'),
(532, '', 'Upplupna avtalade sociala avgifter', '', '', '2951', 'Upplupna avtalade arbetsmarknadsförsäkringar'),
(533, '', 'Upplupna avtalade sociala avgifter', '', '', '2959', 'Upplupna avtalade pensionsförsäkringsavgifter, deklarationspost'),
(534, '296', 'Upplupna räntekostnader', '', '1', '2960', 'Upplupna räntekostnader'),
(535, '297', 'Förutbetalda intäkter', '', '1', '2970', 'Förutbetalda intäkter'),
(536, '', 'Förutbetalda intäkter', '', '', '2971', 'Förutbetalda hyresintäkter'),
(537, '', 'Förutbetalda intäkter', '', '', '2972', 'Förutbetalda medlemsavgifter'),
(538, '', 'Förutbetalda intäkter', '', '', '2979', 'Övriga förutbetalda intäkter'),
(539, '298', 'Upplupna avtalskostnader', '', '', '2980', 'Upplupna avtalskostnader'),
(540, '299', 'Övriga upplupna kostnader och förutbetalda intäkter', '', '1', '2990', 'Övriga upplupna kostnader och förutbetalda intäkter'),
(541, '', 'Övriga upplupna kostnader och förutbetalda intäkter', '', '', '2991', 'Beräknat arvode för bokslut'),
(542, '', 'Övriga upplupna kostnader och förutbetalda intäkter', '', '', '2992', 'Beräknat arvode för revision'),
(543, '', 'Övriga upplupna kostnader och förutbetalda intäkter', '', '', '2993', 'Ospecificerad skuld till leverantörer'),
(544, '', 'Övriga upplupna kostnader och förutbetalda intäkter', '', '1', '2995', 'Ej ankomna leverantörsfakturor'),
(545, '', 'Övriga upplupna kostnader och förutbetalda intäkter', '', '', '2998', 'Övriga upplupna kostnader och förutbetalda intäkter'),
(546, '', 'Övriga upplupna kostnader och förutbetalda intäkter', '', '1', '2999', 'OBS-konto'),
(547, '3', 'Rörelsens inkomster/intäkter', '', '', '', ''),
(548, '30', 'Huvudintäkter', '', '', '', ''),
(549, '300', 'Försäljning inom Sverige', '', '1', '3000', 'Försäljning inom Sverige'),
(550, '', 'Försäljning inom Sverige', '', '1', '3001', 'Försäljning inom Sverige, 25 % moms'),
(551, '', 'Försäljning inom Sverige', '', '1', '3002', 'Försäljning inom Sverige, 12 % moms'),
(552, '', 'Försäljning inom Sverige', '', '1', '3003', 'Försäljning inom Sverige, 6 % moms'),
(553, '', 'Försäljning inom Sverige', '', '1', '3004', 'Försäljning inom Sverige, momsfri'),
(554, '31', 'Huvudintäkter', '', '', '', ''),
(555, '310', 'Försäljning av varor utanför Sverige', '', '1', '3100', 'Försäljning av varor utanför Sverige'),
(556, '', 'Försäljning av varor utanför Sverige', '', '1', '3105', 'Försäljning varor till land utanför EU'),
(557, '', 'Försäljning av varor utanför Sverige', '', '1', '3106', 'Försäljning varor till annat EU-land, momspliktig'),
(558, '', 'Försäljning av varor utanför Sverige', '', '1', '3108', 'Försäljning varor till annat EU-land, momsfri'),
(559, '32', 'Huvudintäkter', '', '', '', ''),
(560, '320', 'Försäljning VMB och omvänd moms', '', '1', '3200', 'Försäljning VMB och omvänd moms'),
(561, '321', 'Försäljning positiv VMB 25 %', '', '1', '3211', 'Försäljning positiv VMB 25 %'),
(562, '', 'Försäljning positiv VMB 25 %', '', '1', '3212', 'Försäljning negativ VMB 25 %'),
(563, '323', 'Försäljning inom byggsektorn, omvänd betalningsskyldighet moms', '', '1', '3231', 'Försäljning inom byggsektorn, omvänd betalningsskyldighet moms'),
(564, '33', 'Huvudintäkter', '', '', '', ''),
(565, '330', 'Försäljning av tjänster utanför Sverige', '', '1', '3300', 'Försäljning av tjänster utanför Sverige'),
(566, '', 'Försäljning av tjänster utanför Sverige', '', '1', '3305', 'Försäljning tjänster till land utanför EU'),
(567, '', 'Försäljning av tjänster utanför Sverige', '', '1', '3308', 'Försäljning tjänster till annat EU-land'),
(568, '34', 'Huvudintäkter', '', '', '', ''),
(569, '340', 'Försäljning, egna uttag', '', '1', '3400', 'Försäljning, egna uttag'),
(570, '', 'Försäljning, egna uttag', '', '1', '3401', 'Egna uttag momspliktiga, 25 %'),
(571, '', 'Försäljning, egna uttag', '', '1', '3402', 'Egna uttag momspliktiga, 12 %'),
(572, '', 'Försäljning, egna uttag', '', '1', '3403', 'Egna uttag momspliktiga, 6 %'),
(573, '', 'Försäljning, egna uttag', '', '1', '3404', 'Egna uttag, momsfria'),
(574, '35', 'Fakturerade kostnader', '', '', '', ''),
(575, '350', 'Fakturerade kostnader (gruppkonto)', '', '1', '3500', 'Fakturerade kostnader (gruppkonto)'),
(576, '351', 'Fakturerat emballage', '', '1', '3510', 'Fakturerat emballage'),
(577, '', 'Fakturerat emballage', '', '', '3511', 'Fakturerat emballage'),
(578, '', 'Fakturerat emballage', '', '', '3518', 'Returnerat emballage'),
(579, '352', 'Fakturerade frakter', '', '1', '3520', 'Fakturerade frakter'),
(580, '', 'Fakturerade frakter', '', '1', '3521', 'Fakturerade frakter, EU-land'),
(581, '', 'Fakturerade frakter', '', '1', '3522', 'Fakturerade frakter, export'),
(582, '353', 'Fakturerade tull- och speditionskostnader m.m.', '', '1', '3530', 'Fakturerade tull- och speditionskostnader m.m.'),
(583, '354', 'Faktureringsavgifter', '', '1', '3540', 'Faktureringsavgifter'),
(584, '', 'Faktureringsavgifter', '', '1', '3541', 'Faktureringsavgifter, EU-land'),
(585, '', 'Faktureringsavgifter', '', '1', '3542', 'Faktureringsavgifter, export'),
(586, '355', 'Fakturerade resekostnader', '', '', '3550', 'Fakturerade resekostnader'),
(587, '356', 'Fakturerade kostnader till koncernföretag', '', '', '3560', 'Fakturerade kostnader till koncernföretag'),
(588, '', 'Fakturerade kostnader till koncernföretag', '', '', '3561', 'Fakturerade kostnader till moderföretag'),
(589, '', 'Fakturerade kostnader till koncernföretag', '', '', '3562', 'Fakturerade kostnader till dotterföretag'),
(590, '', 'Fakturerade kostnader till koncernföretag', '', '', '3563', 'Fakturerade kostnader till andra koncernföretag'),
(591, '357', 'Fakturerade kostnader till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '3570', 'Fakturerade kostnader till intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(592, '359', 'Övriga fakturerade kostnader', '', '', '3590', 'Övriga fakturerade kostnader'),
(593, '36', 'Rörelsens sidointäkter', '', '', '', ''),
(594, '360', 'Rörelsens sidointäkter (gruppkonto)', '', '1', '3600', 'Rörelsens sidointäkter (gruppkonto)'),
(595, '361', 'Försäljning av material', '', '', '3610', 'Försäljning av material'),
(596, '', 'Försäljning av material', '', '', '3611', 'Försäljning av råmaterial'),
(597, '', 'Försäljning av material', '', '', '3612', 'Försäljning av skrot'),
(598, '', 'Försäljning av material', '', '', '3613', 'Försäljning av förbrukningsmaterial'),
(599, '', 'Försäljning av material', '', '', '3619', 'Försäljning av övrigt material'),
(600, '362', 'Tillfällig uthyrning av personal', '', '', '3620', 'Tillfällig uthyrning av personal'),
(601, '363', 'Tillfällig uthyrning av transportmedel', '', '', '3630', 'Tillfällig uthyrning av transportmedel'),
(602, '367', 'Intäkter från värdepapper', '', '', '3670', 'Intäkter från värdepapper'),
(603, '', 'Intäkter från värdepapper', '', '', '3671', 'Försäljning av värdepapper'),
(604, '', 'Intäkter från värdepapper', '', '', '3672', 'Utdelning från värdepapper'),
(605, '', 'Intäkter från värdepapper', '', '', '3679', 'Övriga intäkter från värdepapper'),
(606, '368', 'Management fees', '', '', '3680', 'Management fees'),
(607, '369', 'Övriga sidointäkter', '', '', '3690', 'Övriga sidointäkter'),
(608, '37', 'Intäktskorrigeringar', '', '', '', ''),
(609, '370', 'Intäktskorrigeringar (gruppkonto)', '', '', '3700', 'Intäktskorrigeringar (gruppkonto)'),
(610, '371', 'Ofördelade intäktsreduktioner', '', '', '3710', 'Ofördelade intäktsreduktioner'),
(611, '373', 'Lämnade rabatter', '', '1', '3730', 'Lämnade rabatter'),
(612, '', 'Lämnade rabatter', '', '', '3731', 'Lämnade kassarabatter'),
(613, '', 'Lämnade rabatter', '', '', '3732', 'Lämnade mängdrabatter'),
(614, '374', 'Öres- och kronutjämning', '', '1', '3740', 'Öres- och kronutjämning'),
(615, '375', 'Punktskatter', '', '', '3750', 'Punktskatter'),
(616, '', 'Punktskatter', '', '', '3751', 'Intäktsförda punktskatter (kreditkonto)'),
(617, '', 'Punktskatter', '', '', '3752', 'Skuldförda punktskatter (debetkonto)'),
(618, '379', 'Övriga intäktskorrigeringar', '', '', '3790', 'Övriga intäktskorrigeringar'),
(619, '38', 'Aktiverat arbete för egen räkning', '', '', '', ''),
(620, '380', 'Aktiverat arbete för egen räkning (gruppkonto)', '', '1', '3800', 'Aktiverat arbete för egen räkning (gruppkonto)'),
(621, '384', 'Aktiverat arbete (material)', '', '', '3840', 'Aktiverat arbete (material)'),
(622, '385', 'Aktiverat arbete (omkostnader)', '', '', '3850', 'Aktiverat arbete (omkostnader)'),
(623, '387', 'Aktiverat arbete (personal)', '', '', '3870', 'Aktiverat arbete (personal)'),
(624, '39', 'Övriga rörelseintäkter', '', '', '', ''),
(625, '390', 'Övriga rörelseintäkter (gruppkonto)', '', '1', '3900', 'Övriga rörelseintäkter (gruppkonto)'),
(626, '391', 'Hyres- och arrendeintäkter', '', '', '3910', 'Hyres- och arrendeintäkter'),
(627, '', 'Hyres- och arrendeintäkter', '', '', '3911', 'Hyresintäkter'),
(628, '', 'Hyres- och arrendeintäkter', '', '', '3912', 'Arrendeintäkter'),
(629, '', 'Hyres- och arrendeintäkter', '', '1', '3913', 'Frivilligt momspliktiga hyresintäkter'),
(630, '', 'Hyres- och arrendeintäkter', '', '', '3914', 'Övriga momspliktiga hyresintäkter'),
(631, '392', 'Provisionsintäkter, licensintäkter och royalties', '', '', '3920', 'Provisionsintäkter, licensintäkter och royalties'),
(632, '', 'Provisionsintäkter, licensintäkter och royalties', '', '', '3921', 'Provisionsintäkter'),
(633, '', 'Provisionsintäkter, licensintäkter och royalties', '', '', '3922', 'Licensintäkter och royalties'),
(634, '', 'Provisionsintäkter, licensintäkter och royalties', '', '', '3925', 'Franchiseintäkter'),
(635, '394', 'Orealiserade negativa/positiva värdeförändringar på säkringsinstrument', '1', '', '3940', 'Orealiserade negativa/positiva värdeförändringar på säkringsinstrument'),
(636, '395', 'Återvunna, tidigare avskrivna kundfordringar', '', '', '3950', 'Återvunna, tidigare avskrivna kundfordringar'),
(637, '396', 'Valutakursvinster på fordringar och skulder av rörelsekaraktär', '', '1', '3960', 'Valutakursvinster på fordringar och skulder av rörelsekaraktär'),
(638, '397', 'Vinst vid avyttring av immateriella och materiella anläggningstillgångar', '', '1', '3970', 'Vinst vid avyttring av immateriella och materiella anläggningstillgångar'),
(639, '', 'Vinst vid avyttring av immateriella och materiella anläggningstillgångar', '', '', '3971', 'Vinst vid avyttring av immateriella anläggningstillgångar'),
(640, '', 'Vinst vid avyttring av immateriella och materiella anläggningstillgångar', '', '', '3972', 'Vinst vid avyttring av byggnader och mark'),
(641, '', 'Vinst vid avyttring av immateriella och materiella anläggningstillgångar', '', '', '3973', 'Vinst vid avyttring av maskiner och inventarier'),
(642, '398', 'Erhållna offentliga bidrag', '', '1', '3980', 'Erhållna offentliga bidrag'),
(643, '', 'Erhållna offentliga bidrag', '', '', '3981', 'Erhållna EU-bidrag'),
(644, '', 'Erhållna offentliga bidrag', '', '', '3985', 'Erhållna statliga bidrag'),
(645, '', 'Erhållna offentliga bidrag', '', '', '3987', 'Erhållna kommunala bidrag'),
(646, '', 'Erhållna offentliga bidrag', '', '', '3988', 'Erhållna offentliga bidrag för personal'),
(647, '', 'Erhållna offentliga bidrag', '', '', '3989', 'Övriga erhållna offentliga bidrag'),
(648, '399', 'Övriga ersättningar, bidrag och intäkter', '', '', '3990', 'Övriga ersättningar, bidrag och intäkter'),
(649, '', 'Övriga ersättningar, bidrag och intäkter', '', '', '3991', 'Konfliktersättning'),
(650, '', 'Övriga ersättningar, bidrag och intäkter', '', '', '3992', 'Erhållna skadestånd'),
(651, '', 'Övriga ersättningar, bidrag och intäkter', '', '', '3993', 'Erhållna donationer och gåvor'),
(652, '', 'Övriga ersättningar, bidrag och intäkter', '', '', '3994', 'Försäkringsersättningar'),
(653, '', 'Övriga ersättningar, bidrag och intäkter', '', '', '3995', 'Erhållet ackord på skulder av rörelsekaraktär'),
(654, '', 'Övriga ersättningar, bidrag och intäkter', '', '', '3996', 'Erhållna reklambidrag'),
(655, '', 'Övriga ersättningar, bidrag och intäkter', '', '', '3997', 'Sjuklöneersättning'),
(656, '', 'Övriga ersättningar, bidrag och intäkter', '', '', '3998', 'Återbäring av överskott från försäkringsföretag'),
(657, '', 'Övriga ersättningar, bidrag och intäkter', '', '', '3999', 'Övriga rörelseintäkter'),
(658, '4', 'Utgifter/kostnader för varor, material och vissa köpta tjänster', '', '', '', ''),
(659, '40', 'Inköp av varor och material', '', '', '', ''),
(660, '400', 'Inköp av varor från Sverige', '', '1', '4000', 'Inköp av varor från Sverige'),
(661, '41', 'Inköp av varor och material', '', '', '', ''),
(662, '42', 'Inköp av varor och material', '', '', '', ''),
(663, '420', 'Sålda varor VMB', '', '1', '4200', 'Sålda varor VMB'),
(664, '421', 'Sålda varor VMB 25 %', '', '1', '4211', 'Sålda varor positiv VMB 25 %'),
(665, '', '', '', '1', '4212', 'Sålda varor negativ VMB 25 %'),
(666, '43', 'Inköp av varor och material', '', '', '', ''),
(667, '44', 'Inköp av varor och material', '', '', '', ''),
(668, '440', 'Momspliktiga inköp i Sverige', '', '1', '4400', 'Momspliktiga inköp i Sverige'),
(669, '441', 'Inköpta varor i Sverige, omvänd betalningsskyldighet', '', '1', '4415', 'Inköpta varor i Sverige, omvänd betalningsskyldighet, 25 % moms'),
(670, '', 'Inköpta varor i Sverige, omvänd betalningsskyldighet', '', '', '4416', 'Inköpta varor i Sverige, omvänd betalningsskyldighet, 12 % moms'),
(671, '', 'Inköpta varor i Sverige, omvänd betalningsskyldighet', '', '', '4417', 'Inköpta varor i Sverige, omvänd betalningsskyldighet, 6 % moms'),
(672, '442', 'Inköpta tjänster i Sverige, omvänd betalningsskyldighet', '', '', '4425', 'Inköpta tjänster i Sverige, omvänd betalningsskyldighet, 25 % moms'),
(673, '', 'Inköpta tjänster i Sverige, omvänd betalningsskyldighet', '', '1', '4426', 'Inköpta tjänster i Sverige, omvänd betalningsskyldighet, 12 % moms'),
(674, '', 'Inköpta tjänster i Sverige, omvänd betalningsskyldighet', '', '1', '4427', 'Inköpta tjänster i Sverige, omvänd betalningsskyldighet, 6 % moms'),
(675, '45', 'Inköp av varor och material', '', '', '', ''),
(676, '450', 'Övriga momspliktiga inköp', '', '1', '4500', 'Övriga momspliktiga inköp'),
(677, '451', 'Inköp av varor från annat EU-land', '', '1', '4515', 'Inköp av varor från annat EU-land, 25 %'),
(678, '', 'Inköp av varor från annat EU-land', '', '1', '4516', 'Inköp av varor från annat EU-land, 12 %'),
(679, '', 'Inköp av varor från annat EU-land', '', '1', '4517', 'Inköp av varor från annat EU-land, 6 %'),
(680, '', 'Inköp av varor från annat EU-land', '', '1', '4518', 'Inköp av varor från annat EU-land, momsfri'),
(681, '453', 'Inköp av tjänster från ett land utanför EU', '', '1', '4531', 'Inköp av tjänster från ett land utanför EU, 25 % moms'),
(682, '', 'Inköp av tjänster från ett land utanför EU', '', '1', '4532', 'Inköp av tjänster från ett land utanför EU, 12 % moms'),
(683, '', 'Inköp av tjänster från ett land utanför EU', '', '1', '4533', 'Inköp av tjänster från ett land utanför EU, 6 % moms'),
(684, '', 'Inköp av tjänster från ett land utanför EU', '', '1', '4535', 'Inköp av tjänster från annat EU-land, 25 %'),
(685, '', 'Inköp av tjänster från ett land utanför EU', '', '1', '4536', 'Inköp av tjänster från annat EU-land, 12 %'),
(686, '', 'Inköp av tjänster från ett land utanför EU', '', '1', '4537', 'Inköp av tjänster från annat EU-land, 6 %'),
(687, '', 'Inköp av tjänster från ett land utanför EU', '', '1', '4538', 'Inköp av tjänster från annat EU-land, momsfri'),
(688, '454', 'Import av varor', '', '1', '4545', 'Import av varor, 25 % moms'),
(689, '', 'Import av varor', '', '1', '4546', 'Import av varor, 12 % moms'),
(690, '', 'Import av varor', '', '1', '4547', 'Import av varor, 6 % moms'),
(691, '46', 'Legoarbeten, underentreprenader', '', '', '', ''),
(692, '460', 'Legoarbeten och underentreprenader (gruppkonto)', '', '1', '4600', 'Legoarbeten och underentreprenader (gruppkonto)'),
(693, '47', 'Reduktion av inköpspriser', '', '', '', ''),
(694, '470', 'Reduktion av inköpspriser (gruppkonto)', '', '1', '4700', 'Reduktion av inköpspriser (gruppkonto)'),
(695, '473', 'Erhållna rabatter', '', '', '4730', 'Erhållna rabatter'),
(696, '', 'Erhållna rabatter', '', '', '4731', 'Erhållna kassarabatter'),
(697, '', 'Erhållna rabatter', '', '', '4732', 'Erhållna mängdrabatter (inkl. bonus)'),
(698, '', 'Erhållna rabatter', '', '', '4733', 'Erhållet aktivitetsstöd'),
(699, '479', 'Övriga reduktioner av inköpspriser', '', '', '4790', 'Övriga reduktioner av inköpspriser'),
(700, '48', '(Fri kontogrupp)', '', '', '', ''),
(701, '49', 'Förändring av lager, produkter i arbete och pågående arbeten', '', '', '', ''),
(702, '490', 'Förändring av lager (gruppkonto)', '', '1', '4900', 'Förändring av lager (gruppkonto)'),
(703, '491', 'Förändring av lager av råvaror', '', '1', '4910', 'Förändring av lager av råvaror'),
(704, '492', 'Förändring av lager av tillsatsmaterial och förnödenheter', '', '1', '4920', 'Förändring av lager av tillsatsmaterial och förnödenheter'),
(705, '494', 'Förändring av produkter i arbete', '', '1', '4940', 'Förändring av produkter i arbete'),
(706, '', 'Förändring av produkter i arbete', '', '', '4944', 'Förändring av produkter i arbete, material och utlägg'),
(707, '', 'Förändring av produkter i arbete', '', '', '4945', 'Förändring av produkter i arbete, omkostnader'),
(708, '', 'Förändring av produkter i arbete', '', '', '4947', 'Förändring av produkter i arbete, personalkostnader'),
(709, '495', 'Förändring av lager av färdiga varor', '', '1', '4950', 'Förändring av lager av färdiga varor'),
(710, '496', 'Förändring av lager av handelsvaror', '', '1', '4960', 'Förändring av lager av handelsvaror'),
(711, '497', 'Förändring av pågående arbeten, nedlagda kostnader', '', '1', '4970', 'Förändring av pågående arbeten, nedlagda kostnader'),
(712, '', 'Förändring av pågående arbeten, nedlagda kostnader', '', '', '4974', 'Förändring av pågående arbeten, material och utlägg'),
(713, '', 'Förändring av pågående arbeten, nedlagda kostnader', '', '', '4975', 'Förändring av pågående arbeten, omkostnader'),
(714, '', 'Förändring av pågående arbeten, nedlagda kostnader', '', '', '4977', 'Förändring av pågående arbeten, personalkostnader'),
(715, '498', 'Förändring av lager av värdepapper', '', '', '4980', 'Förändring av lager av värdepapper'),
(716, '', 'Förändring av lager av värdepapper', '', '', '4981', 'Sålda värdepappers anskaffningsvärde'),
(717, '', 'Förändring av lager av värdepapper', '', '', '4987', 'Nedskrivning av värdepapper'),
(718, '', 'Förändring av lager av värdepapper', '', '', '4988', 'Återföring av nedskrivning av värdepapper'),
(719, '5', 'Övriga externa rörelseutgifter/ kostnader', '', '', '', ''),
(720, '50', 'Lokalkostnader', '', '', '', ''),
(721, '500', 'Lokalkostnader (gruppkonto)', '', '', '5000', 'Lokalkostnader (gruppkonto)'),
(722, '501', 'Lokalhyra', '', '1', '5010', 'Lokalhyra'),
(723, '', 'Lokalhyra', '', '', '5011', 'Hyra för kontorslokaler'),
(724, '', 'Lokalhyra', '', '', '5012', 'Hyra för garage'),
(725, '', 'Lokalhyra', '', '', '5013', 'Hyra för lagerlokaler'),
(726, '502', 'El för belysning', '', '1', '5020', 'El för belysning'),
(727, '503', 'Värme', '', '1', '5030', 'Värme'),
(728, '504', 'Vatten och avlopp', '', '1', '5040', 'Vatten och avlopp'),
(729, '505', 'Lokaltillbehör', '', '', '5050', 'Lokaltillbehör'),
(730, '506', 'Städning och renhållning', '', '1', '5060', 'Städning och renhållning'),
(731, '', 'Städning och renhållning', '', '', '5061', 'Städning'),
(732, '', 'Städning och renhållning', '', '', '5062', 'Sophämtning'),
(733, '', 'Städning och renhållning', '', '', '5063', 'Hyra för sopcontainer'),
(734, '', 'Städning och renhållning', '', '', '5064', 'Snöröjning'),
(735, '', 'Städning och renhållning', '', '', '5065', 'Trädgårdsskötsel'),
(736, '507', 'Reparation och underhåll av lokaler', '', '1', '5070', 'Reparation och underhåll av lokaler'),
(737, '509', 'Övriga lokalkostnader', '', '', '5090', 'Övriga lokalkostnader'),
(738, '', 'Övriga lokalkostnader', '', '', '5098', 'Övriga lokalkostnader, avdragsgilla'),
(739, '', 'Övriga lokalkostnader', '', '', '5099', 'Övriga lokalkostnader, ej avdragsgilla'),
(740, '51', 'Fastighetskostnader', '', '', '', ''),
(741, '510', 'Fastighetskostnader (gruppkonto)', '', '', '5100', 'Fastighetskostnader (gruppkonto)'),
(742, '511', 'Tomträttsavgäld/arrende', '', '', '5110', 'Tomträttsavgäld/arrende'),
(743, '512', 'El för belysning', '', '1', '5120', 'El för belysning'),
(744, '513', 'Värme', '', '1', '5130', 'Värme'),
(745, '', 'Värme', '', '', '5131', 'Uppvärmning'),
(746, '', 'Värme', '', '', '5132', 'Sotning'),
(747, '514', 'Vatten och avlopp', '', '1', '5140', 'Vatten och avlopp'),
(748, '516', 'Städning och renhållning', '', '1', '5160', 'Städning och renhållning'),
(749, '', 'Städning och renhållning', '', '', '5161', 'Städning'),
(750, '', 'Städning och renhållning', '', '', '5162', 'Sophämtning'),
(751, '', 'Städning och renhållning', '', '', '5163', 'Hyra för sopcontainer'),
(752, '', 'Städning och renhållning', '', '', '5164', 'Snöröjning'),
(753, '', 'Städning och renhållning', '', '', '5165', 'Trädgårdsskötsel'),
(754, '517', 'Reparation och underhåll av fastighet', '', '1', '5170', 'Reparation och underhåll av fastighet'),
(755, '519', 'Övriga fastighetskostnader', '', '', '5190', 'Övriga fastighetskostnader'),
(756, '', 'Övriga fastighetskostnader', '', '', '5191', 'Fastighetsskatt/fastighetsavgift'),
(757, '', 'Övriga fastighetskostnader', '', '', '5192', 'Fastighetsförsäkringspremier'),
(758, '', 'Övriga fastighetskostnader', '', '', '5193', 'Fastighetsskötsel och förvaltning'),
(759, '', 'Övriga fastighetskostnader', '', '', '5198', 'Övriga fastighetskostnader, avdragsgilla'),
(760, '', 'Övriga fastighetskostnader', '', '', '5199', 'Övriga fastighetskostnader, ej avdragsgilla'),
(761, '52', 'Hyra av anläggningstillgångar', '', '', '', ''),
(762, '520', 'Hyra av anläggningstillgångar (gruppkonto)', '', '1', '5200', 'Hyra av anläggningstillgångar (gruppkonto)'),
(763, '521', 'Hyra av maskiner och andra tekniska anläggningar', '', '', '5210', 'Hyra av maskiner och andra tekniska anläggningar'),
(764, '', 'Hyra av maskiner och andra tekniska anläggningar', '', '', '5211', 'Korttidshyra av maskiner och andra tekniska anläggningar'),
(765, '', 'Hyra av maskiner och andra tekniska anläggningar', '', '', '5212', 'Leasing av maskiner och andra tekniska anläggningar'),
(766, '522', 'Hyra av inventarier och verktyg', '', '', '5220', 'Hyra av inventarier och verktyg'),
(767, '', 'Hyra av inventarier och verktyg', '', '', '5221', 'Korttidshyra av inventarier och verktyg'),
(768, '', 'Hyra av inventarier och verktyg', '', '', '5222', 'Leasing av inventarier och verktyg'),
(769, '525', 'Hyra av datorer', '', '', '5250', 'Hyra av datorer'),
(770, '', 'Hyra av datorer', '', '', '5251', 'Korttidshyra av datorer'),
(771, '', 'Hyra av datorer', '', '', '5252', 'Leasing av datorer'),
(772, '529', 'Övriga hyreskostnader för anläggningstillgångar', '', '', '5290', 'Övriga hyreskostnader för anläggningstillgångar'),
(773, '53', 'Energikostnader', '', '', '', ''),
(774, '530', 'Energikostnader (gruppkonto)', '', '1', '5300', 'Energikostnader (gruppkonto)'),
(775, '531', 'El för drift', '', '', '5310', 'El för drift'),
(776, '532', 'Gas', '', '', '5320', 'Gas'),
(777, '533', 'Eldningsolja', '', '', '5330', 'Eldningsolja'),
(778, '534', 'Stenkol och koks', '', '', '5340', 'Stenkol och koks'),
(779, '535', 'Torv, träkol, ved och annat träbränsle', '', '', '5350', 'Torv, träkol, ved och annat träbränsle'),
(780, '536', 'Bensin, fotogen och motorbrännolja', '', '', '5360', 'Bensin, fotogen och motorbrännolja'),
(781, '537', 'Fjärrvärme, kyla och ånga', '', '', '5370', 'Fjärrvärme, kyla och ånga'),
(782, '538', 'Vatten', '', '', '5380', 'Vatten'),
(783, '539', 'Övriga energikostnader', '', '', '5390', 'Övriga energikostnader'),
(784, '54', 'Förbrukningsinventarier och förbrukningsmaterial', '', '', '', ''),
(785, '540', 'Förbrukningsinventarier och förbrukningsmaterial (gruppkonto)', '', '', '5400', 'Förbrukningsinventarier och förbrukningsmaterial (gruppkonto)'),
(786, '541', 'Förbrukningsinventarier', '', '1', '5410', 'Förbrukningsinventarier'),
(787, '', 'Förbrukningsinventarier', '', '', '5411', 'Förbrukningsinventarier med en livslängd på mer än ett år'),
(788, '', 'Förbrukningsinventarier', '', '', '5412', 'Förbrukningsinventarier med en livslängd på ett år eller mindre'),
(789, '542', 'Programvaror', '', '1', '5420', 'Programvaror'),
(790, '543', 'Transportinventarier', '', '', '5430', 'Transportinventarier'),
(791, '544', 'Förbrukningsemballage', '', '', '5440', 'Förbrukningsemballage'),
(792, '546', 'Förbrukningsmaterial', '', '1', '5460', 'Förbrukningsmaterial'),
(793, '548', 'Arbetskläder och skyddsmaterial', '', '', '5480', 'Arbetskläder och skyddsmaterial'),
(794, '549', 'Övriga förbrukningsinventarier och förbrukningsmaterial', '', '', '5490', 'Övriga förbrukningsinventarier och förbrukningsmaterial'),
(795, '', 'Övriga förbrukningsinventarier och förbrukningsmaterial', '', '', '5491', 'Övriga förbrukningsinventarier med en livslängd på mer än ett år'),
(796, '', 'Övriga förbrukningsinventarier och förbrukningsmaterial', '', '', '5492', 'Övriga förbrukningsinventarier med en livslängd på ett år eller mindre'),
(797, '', 'Övriga förbrukningsinventarier och förbrukningsmaterial', '', '', '5493', 'Övrigt förbrukningsmaterial'),
(798, '55', 'Reparation och underhåll', '', '', '', ''),
(799, '550', 'Reparation och underhåll (gruppkonto)', '', '1', '5500', 'Reparation och underhåll (gruppkonto)'),
(800, '551', 'Reparation och underhåll av maskiner och andra tekniska anläggningar', '', '', '5510', 'Reparation och underhåll av maskiner och andra tekniska anläggningar'),
(801, '552', 'Reparation och underhåll av inventarier, verktyg och datorer m.m.', '', '', '5520', 'Reparation och underhåll av inventarier, verktyg och datorer m.m.'),
(802, '553', 'Reparation och underhåll av installationer', '', '', '5530', 'Reparation och underhåll av installationer'),
(803, '555', 'Reparation och underhåll av förbrukningsinventarier', '', '', '5550', 'Reparation och underhåll av förbrukningsinventarier'),
(804, '558', 'Underhåll och tvätt av arbetskläder', '', '', '5580', 'Underhåll och tvätt av arbetskläder'),
(805, '559', 'Övriga kostnader för reparation och underhåll', '', '', '5590', 'Övriga kostnader för reparation och underhåll'),
(806, '56', 'Kostnader för transportmedel', '', '', '', ''),
(807, '560', 'Kostnader för transportmedel (gruppkonto)', '', '1', '5600', 'Kostnader för transportmedel (gruppkonto)'),
(808, '561', 'Personbilskostnader', '', '', '5610', 'Personbilskostnader'),
(809, '', 'Personbilskostnader', '', '1', '5611', 'Drivmedel för personbilar'),
(810, '', 'Personbilskostnader', '', '1', '5612', 'Försäkring och skatt för personbilar'),
(811, '', 'Personbilskostnader', '', '1', '5613', 'Reparation och underhåll av personbilar'),
(812, '', 'Personbilskostnader', '', '1', '5615', 'Leasing av personbilar'),
(813, '', 'Personbilskostnader', '', '', '5616', 'Trängselskatt, avdragsgill'),
(814, '', 'Personbilskostnader', '', '', '5619', 'Övriga personbilskostnader'),
(815, '562', 'Lastbilskostnader', '', '', '5620', 'Lastbilskostnader'),
(816, '563', 'Truckkostnader', '', '', '5630', 'Truckkostnader'),
(817, '564', 'Kostnader för arbetsmaskiner', '', '', '5640', 'Kostnader för arbetsmaskiner'),
(818, '565', 'Traktorkostnader', '', '', '5650', 'Traktorkostnader'),
(819, '566', 'Motorcykel-, moped- och skoterkostnader', '', '', '5660', 'Motorcykel-, moped- och skoterkostnader'),
(820, '567', 'Båt-, flygplans- och helikopterkostnader', '', '', '5670', 'Båt-, flygplans- och helikopterkostnader'),
(821, '569', 'Övriga kostnader för transportmedel', '', '', '5690', 'Övriga kostnader för transportmedel'),
(822, '57', 'Frakter och transporter', '', '', '', ''),
(823, '570', 'Frakter och transporter (gruppkonto)', '', '1', '5700', 'Frakter och transporter (gruppkonto)'),
(824, '571', 'Frakter, transporter och försäkringar vid varudistribution', '', '', '5710', 'Frakter, transporter och försäkringar vid varudistribution'),
(825, '572', 'Tull- och speditionskostnader m.m.', '', '', '5720', 'Tull- och speditionskostnader m.m.'),
(826, '573', 'Arbetstransporter', '', '', '5730', 'Arbetstransporter'),
(827, '579', 'Övriga kostnader för frakter och transporter', '', '', '5790', 'Övriga kostnader för frakter och transporter'),
(828, '58', 'Resekostnader', '', '', '', ''),
(829, '580', 'Resekostnader (gruppkonto)', '', '1', '5800', 'Resekostnader (gruppkonto)'),
(830, '581', 'Biljetter', '', '1', '5810', 'Biljetter'),
(831, '582', 'Hyrbilskostnader', '', '1', '5820', 'Hyrbilskostnader'),
(832, '583', 'Kost och logi', '', '', '5830', 'Kost och logi'),
(833, '', 'Kost och logi', '', '1', '5831', 'Kost och logi i Sverige'),
(834, '', 'Kost och logi', '', '1', '5832', 'Kost och logi i utlandet'),
(835, '589', 'Övriga resekostnader', '', '', '5890', 'Övriga resekostnader'),
(836, '59', 'Reklam och PR', '', '', '', ''),
(837, '590', 'Reklam och PR (gruppkonto)', '', '1', '5900', 'Reklam och PR (gruppkonto)'),
(838, '591', 'Annonsering', '', '', '5910', 'Annonsering'),
(839, '592', 'Utomhus- och trafikreklam', '', '', '5920', 'Utomhus- och trafikreklam'),
(840, '593', 'Reklamtrycksaker och direktreklam', '', '', '5930', 'Reklamtrycksaker och direktreklam'),
(841, '594', 'Utställningar och mässor', '', '', '5940', 'Utställningar och mässor'),
(842, '595', 'Butiksreklam och återförsäljarreklam', '', '', '5950', 'Butiksreklam och återförsäljarreklam'),
(843, '596', 'Varuprover, reklamgåvor, presentreklam och tävlingar', '', '', '5960', 'Varuprover, reklamgåvor, presentreklam och tävlingar'),
(844, '597', 'Film-, radio-, TV- och Internetreklam', '', '', '5970', 'Film-, radio-, TV- och Internetreklam'),
(845, '598', 'PR, institutionell reklam och sponsring', '', '', '5980', 'PR, institutionell reklam och sponsring'),
(846, '599', 'Övriga kostnader för reklam och PR', '', '', '5990', 'Övriga kostnader för reklam och PR'),
(847, '6', 'Övriga externa rörelseutgifter/ kostnader', '', '', '', ''),
(848, '60', 'Övriga försäljningskostnader', '', '', '', ''),
(849, '600', 'Övriga försäljningskostnader (gruppkonto)', '', '', '6000', 'Övriga försäljningskostnader (gruppkonto)'),
(850, '601', 'Kataloger, prislistor m.m.', '', '', '6010', 'Kataloger, prislistor m.m.'),
(851, '602', 'Egna facktidskrifter', '', '', '6020', 'Egna facktidskrifter'),
(852, '603', 'Speciella orderkostnader', '', '', '6030', 'Speciella orderkostnader'),
(853, '604', 'Kontokortsavgifter', '', '', '6040', 'Kontokortsavgifter'),
(854, '605', 'Försäljningsprovisioner', '', '', '6050', 'Försäljningsprovisioner'),
(855, '', '', '', '', '6055', 'Franchisekostnader o.dyl.'),
(856, '606', 'Kreditförsäljningskostnader', '', '', '6060', 'Kreditförsäljningskostnader'),
(857, '', 'Kreditförsäljningskostnader', '', '', '6061', 'Kreditupplysning'),
(858, '', 'Kreditförsäljningskostnader', '', '', '6062', 'Inkasso och KFM-avgifter'),
(859, '', 'Kreditförsäljningskostnader', '', '', '6063', 'Kreditförsäkringspremier'),
(860, '', 'Kreditförsäljningskostnader', '', '', '6064', 'Factoringavgifter'),
(861, '', 'Kreditförsäljningskostnader', '', '', '6069', 'Övriga kreditförsäljningskostnader'),
(862, '607', 'Representation', '', '', '6070', 'Representation'),
(863, '', 'Representation', '', '1', '6071', 'Representation, avdragsgill'),
(864, '', 'Representation', '', '1', '6072', 'Representation, ej avdragsgill'),
(865, '608', 'Bankgarantier', '', '', '6080', 'Bankgarantier'),
(866, '609', 'Övriga försäljningskostnader', '', '1', '6090', 'Övriga försäljningskostnader'),
(867, '61', 'Kontorsmateriel och trycksaker', '', '', '', ''),
(868, '610', 'Kontorsmateriel och trycksaker (gruppkonto)', '', '1', '6100', 'Kontorsmateriel och trycksaker (gruppkonto)'),
(869, '611', 'Kontorsmateriel', '', '', '6110', 'Kontorsmateriel'),
(870, '615', 'Trycksaker', '', '', '6150', 'Trycksaker'),
(871, '62', 'Tele och post', '', '', '', ''),
(872, '620', 'Tele och post (gruppkonto)', '', '', '6200', 'Tele och post (gruppkonto)'),
(873, '621', 'Telekommunikation', '', '1', '6210', 'Telekommunikation'),
(874, '', 'Telekommunikation', '', '', '6211', 'Fast telefoni'),
(875, '', 'Telekommunikation', '', '', '6212', 'Mobiltelefon'),
(876, '', 'Telekommunikation', '', '', '6213', 'Mobilsökning'),
(877, '', 'Telekommunikation', '', '', '6214', 'Fax'),
(878, '', 'Telekommunikation', '', '', '6215', 'Telex'),
(879, '623', 'Datakommunikation', '', '', '6230', 'Datakommunikation'),
(880, '625', 'Postbefordran', '', '1', '6250', 'Postbefordran'),
(881, '63', 'Företagsförsäkringar och övriga riskkostnader', '', '', '', ''),
(882, '630', 'Företagsförsäkringar och övriga riskkostnader (gruppkonto)', '', '', '6300', 'Företagsförsäkringar och övriga riskkostnader (gruppkonto)'),
(883, '631', 'Företagsförsäkringar', '', '1', '6310', 'Företagsförsäkringar'),
(884, '632', 'Självrisker vid skada', '', '', '6320', 'Självrisker vid skada'),
(885, '633', 'Förluster i pågående arbeten', '', '', '6330', 'Förluster i pågående arbeten'),
(886, '634', 'Lämnade skadestånd', '', '', '6340', 'Lämnade skadestånd'),
(887, '', 'Lämnade skadestånd', '', '', '6341', 'Lämnade skadestånd, avdragsgilla'),
(888, '', 'Lämnade skadestånd', '', '', '6342', 'Lämnade skadestånd, ej avdragsgilla'),
(889, '635', 'Förluster på kundfordringar', '', '1', '6350', 'Förluster på kundfordringar'),
(890, '', 'Förluster på kundfordringar', '', '', '6351', 'Konstaterade förluster på kundfordringar'),
(891, '', 'Förluster på kundfordringar', '', '', '6352', 'Befarade förluster på kundfordringar'),
(892, '636', 'Garantikostnader', '', '', '6360', 'Garantikostnader'),
(893, '', 'Garantikostnader', '', '', '6361', 'Förändring av garantiavsättning'),
(894, '', 'Garantikostnader', '', '', '6362', 'Faktiska garantikostnader'),
(895, '637', 'Kostnader för bevakning och larm', '', '', '6370', 'Kostnader för bevakning och larm'),
(896, '638', 'Förluster på övriga kortfristiga fordringar', '', '', '6380', 'Förluster på övriga kortfristiga fordringar'),
(897, '639', 'Övriga riskkostnader', '', '1', '6390', 'Övriga riskkostnader'),
(898, '64', 'Förvaltningskostnader', '', '', '', ''),
(899, '640', 'Förvaltningskostnader (gruppkonto)', '', '', '6400', 'Förvaltningskostnader (gruppkonto)'),
(900, '641', 'Styrelsearvoden som inte är lön', '', '1', '6410', 'Styrelsearvoden som inte är lön'),
(901, '642', 'Ersättningar till revisor', '', '1', '6420', 'Ersättningar till revisor'),
(902, '', 'Ersättningar till revisor', '', '', '6421', 'Revision'),
(903, '', 'Ersättningar till revisor', '', '', '6422', 'Revisonsverksamhet utöver revision'),
(904, '', 'Ersättningar till revisor', '', '', '6423', 'Skatterådgivning – revisor'),
(905, '', 'Ersättningar till revisor', '', '', '6424', 'Övriga tjänster – revisor'),
(906, '643', 'Management fees', '', '', '6430', 'Management fees'),
(907, '644', 'Årsredovisning och delårsrapporter', '', '', '6440', 'Årsredovisning och delårsrapporter'),
(908, '645', 'Bolagsstämma/års- eller föreningsstämma', '', '', '6450', 'Bolagsstämma/års- eller föreningsstämma'),
(909, '649', 'Övriga förvaltningskostnader', '', '', '6490', 'Övriga förvaltningskostnader'),
(910, '65', 'Övriga externa tjänster', '', '', '', ''),
(911, '650', 'Övriga externa tjänster (gruppkonto)', '', '', '6500', 'Övriga externa tjänster (gruppkonto)'),
(912, '651', 'Mätningskostnader', '', '', '6510', 'Mätningskostnader'),
(913, '652', 'Ritnings- och kopieringskostnader', '', '', '6520', 'Ritnings- och kopieringskostnader'),
(914, '653', 'Redovisningstjänster', '', '1', '6530', 'Redovisningstjänster'),
(915, '654', 'IT-tjänster', '', '1', '6540', 'IT-tjänster'),
(916, '655', 'Konsultarvoden', '', '1', '6550', 'Konsultarvoden'),
(917, '', 'Konsultarvoden', '', '', '6551', 'Arkitekttjänster'),
(918, '', 'Konsultarvoden', '', '', '6552', 'Teknisk provning och analys'),
(919, '', 'Konsultarvoden', '', '', '6553', 'Tekniska konsulttjänster'),
(920, '', 'Konsultarvoden', '', '', '6554', 'Finansiell- och övrig ekonomisk rådgivning'),
(921, '', 'Konsultarvoden', '', '', '6555', 'Skatterådgivning inkl. insolvens- och konkursförvaltning'),
(922, '', 'Konsultarvoden', '', '', '6556', 'Köpta tjänster avseende forskning och utveckling'),
(923, '', 'Konsultarvoden', '', '', '6559', 'Övrig konsultverksamhet'),
(924, '656', 'Serviceavgifter till branschorganisationer', '', '1', '6560', 'Serviceavgifter till branschorganisationer'),
(925, '657', 'Bankkostnader', '', '1', '6570', 'Bankkostnader'),
(926, '658', 'Advokat- och rättegångskostnader', '', '', '6580', 'Advokat- och rättegångskostnader'),
(927, '659', 'Övriga externa tjänster', '', '1', '6590', 'Övriga externa tjänster'),
(928, '66', '(Fri kontogrupp)', '', '', '', ''),
(929, '67', '(Fri kontogrupp)', '', '', '', ''),
(930, '68', 'Inhyrd personal', '', '', '', ''),
(931, '680', 'Inhyrd personal (gruppkonto)', '', '1', '6800', 'Inhyrd personal (gruppkonto)'),
(932, '681', 'Inhyrd produktionspersonal', '', '', '6810', 'Inhyrd produktionspersonal'),
(933, '682', 'Inhyrd lagerpersonal', '', '', '6820', 'Inhyrd lagerpersonal'),
(934, '683', 'Inhyrd transportpersonal', '', '', '6830', 'Inhyrd transportpersonal'),
(935, '684', 'Inhyrd kontors- och ekonomipersonal', '', '', '6840', 'Inhyrd kontors- och ekonomipersonal'),
(936, '685', 'Inhyrd IT-personal', '', '', '6850', 'Inhyrd IT-personal'),
(937, '686', 'Inhyrd marknads- och försäljningspersonal', '', '', '6860', 'Inhyrd marknads- och försäljningspersonal'),
(938, '687', 'Inhyrd restaurang- och butikspersonal', '', '', '6870', 'Inhyrd restaurang- och butikspersonal'),
(939, '688', 'Inhyrda företagsledare', '', '', '6880', 'Inhyrda företagsledare'),
(940, '689', 'Övrig inhyrd personal', '', '', '6890', 'Övrig inhyrd personal'),
(941, '69', 'Övriga externa kostnader', '', '', '', ''),
(942, '690', 'Övriga externa kostnader (gruppkonto)', '', '', '6900', 'Övriga externa kostnader (gruppkonto)'),
(943, '691', 'Licensavgifter och royalties', '', '', '6910', 'Licensavgifter och royalties'),
(944, '692', 'Kostnader för egna patent', '', '', '6920', 'Kostnader för egna patent'),
(945, '693', 'Kostnader för varumärken m.m.', '', '', '6930', 'Kostnader för varumärken m.m.'),
(946, '694', 'Kontroll-, provnings- och stämpelavgifter', '', '', '6940', 'Kontroll-, provnings- och stämpelavgifter'),
(947, '695', 'Tillsynsavgifter myndigheter', '', '', '6950', 'Tillsynsavgifter myndigheter'),
(948, '697', 'Tidningar, tidskrifter och facklitteratur', '', '1', '6970', 'Tidningar, tidskrifter och facklitteratur'),
(949, '698', 'Föreningsavgifter', '', '1', '6980', 'Föreningsavgifter'),
(950, '', 'Föreningsavgifter', '', '', '6981', 'Föreningsavgifter, avdragsgilla'),
(951, '', 'Föreningsavgifter', '', '', '6982', 'Föreningsavgifter, ej avdragsgilla'),
(952, '699', 'Övriga externa kostnader', '', '', '6990', 'Övriga externa kostnader'),
(953, '', 'Övriga externa kostnader', '', '1', '6991', 'Övriga externa kostnader, avdragsgilla'),
(954, '', 'Övriga externa kostnader', '', '1', '6992', 'Övriga externa kostnader, ej avdragsgilla'),
(955, '', 'Övriga externa kostnader', '', '', '6993', 'Lämnade bidrag och gåvor'),
(956, '', 'Övriga externa kostnader', '', '', '6996', 'Betald utländsk inkomstskatt'),
(957, '', 'Övriga externa kostnader', '', '', '6997', 'Obetald utländsk inkomstskatt'),
(958, '', 'Övriga externa kostnader', '', '', '6998', 'Utländsk moms'),
(959, '', 'Övriga externa kostnader', '', '', '6999', 'Ingående moms, blandad verksamhet'),
(960, '7', 'Utgifter/kostnader för personal, avskrivningar m.m.', '', '', '', ''),
(961, '70', 'Löner till kollektivanställda', '', '', '', ''),
(962, '700', 'Löner till kollektivanställda (gruppkonto)', '', '', '7000', 'Löner till kollektivanställda (gruppkonto)'),
(963, '701', 'Löner till kollektivanställda', '', '1', '7010', 'Löner till kollektivanställda'),
(964, '', 'Löner till kollektivanställda', '', '', '7011', 'Löner till kollektivanställda'),
(965, '', 'Löner till kollektivanställda', '', '', '7012', 'Vinstandelar till kollektivanställda'),
(966, '', 'Löner till kollektivanställda', '', '', '7013', 'Lön växa-stöd kollektivanställda 10,21 %'),
(967, '', 'Löner till kollektivanställda', '', '', '7017', 'Avgångsvederlag till kollektivanställda'),
(968, '', 'Löner till kollektivanställda', '', '', '7018', 'Bruttolöneavdrag, kollektivanställda'),
(969, '', 'Löner till kollektivanställda', '', '', '7019', 'Upplupna löner och vinstandelar till kollektivanställda'),
(970, '703', 'Löner till kollektivanställda (utlandsanställda)', '', '', '7030', 'Löner till kollektivanställda (utlandsanställda)'),
(971, '', 'Löner till kollektivanställda (utlandsanställda)', '', '', '7031', 'Löner till kollektivanställda (utlandsanställda)'),
(972, '', 'Löner till kollektivanställda (utlandsanställda)', '', '', '7032', 'Vinstandelar till kollektivanställda (utlandsanställda)'),
(973, '', 'Löner till kollektivanställda (utlandsanställda)', '', '', '7037', 'Avgångsvederlag till kollektivanställda (utlandsanställda)'),
(974, '', 'Löner till kollektivanställda (utlandsanställda)', '', '', '7038', 'Bruttolöneavdrag, kollektivanställda (utlandsanställda)'),
(975, '', 'Löner till kollektivanställda (utlandsanställda)', '', '', '7039', 'Upplupna löner och vinstandelar till kollektivanställda (utlandsanställda)'),
(976, '708', 'Löner till kollektivanställda för ej arbetad tid', '', '', '7080', 'Löner till kollektivanställda för ej arbetad tid'),
(977, '', 'Löner till kollektivanställda för ej arbetad tid', '', '', '7081', 'Sjuklöner till kollektivanställda'),
(978, '', 'Löner till kollektivanställda för ej arbetad tid', '', '', '7082', 'Semesterlöner till kollektivanställda'),
(979, '', 'Löner till kollektivanställda för ej arbetad tid', '', '', '7083', 'Föräldraersättning till kollektivanställda'),
(980, '', 'Löner till kollektivanställda för ej arbetad tid', '', '', '7089', 'Övriga löner till kollektivanställda för ej arbetad tid'),
(981, '709', 'Förändring av semesterlöneskuld', '', '1', '7090', 'Förändring av semesterlöneskuld'),
(982, '71', '(Fri kontogrupp)', '', '', '', ''),
(983, '72', 'Löner till tjänstemän och företagsledare', '', '', '', ''),
(984, '720', 'Löner till tjänstemän och företagsledare (gruppkonto)', '', '', '7200', 'Löner till tjänstemän och företagsledare (gruppkonto)'),
(985, '721', 'Löner till tjänstemän', '', '1', '7210', 'Löner till tjänstemän'),
(986, '', 'Löner till tjänstemän', '', '', '7211', 'Löner till tjänstemän'),
(987, '', 'Löner till tjänstemän', '', '', '7212', 'Vinstandelar till tjänstemän'),
(988, '', 'Löner till tjänstemän', '', '', '7213', 'Lön växa-stöd tjänstemän 10,21 %'),
(989, '', 'Löner till tjänstemän', '', '', '7217', 'Avgångsvederlag till tjänstemän'),
(990, '', 'Löner till tjänstemän', '', '', '7218', 'Bruttolöneavdrag, tjänstemän'),
(991, '', 'Löner till tjänstemän', '', '', '7219', 'Upplupna löner och vinstandelar till tjänstemän'),
(992, '722', 'Löner till företagsledare', '', '1', '7220', 'Löner till företagsledare'),
(993, '', 'Löner till företagsledare', '', '', '7221', 'Löner till företagsledare'),
(994, '', 'Löner till företagsledare', '', '', '7222', 'Tantiem till företagsledare'),
(995, '', 'Löner till företagsledare', '', '', '7227', 'Avgångsvederlag till företagsledare'),
(996, '', 'Löner till företagsledare', '', '', '7228', 'Bruttolöneavdrag, företagsledare'),
(997, '', 'Löner till företagsledare', '', '', '7229', 'Upplupna löner och tantiem till företagsledare'),
(998, '723', 'Löner till tjänstemän och ftgsledare (utlandsanställda)', '', '', '7230', 'Löner till tjänstemän och ftgsledare (utlandsanställda)'),
(999, '', 'Löner till tjänstemän och ftgsledare (utlandsanställda)', '', '', '7231', 'Löner till tjänstemän och ftgsledare (utlandsanställda)'),
(1000, '', 'Löner till tjänstemän och ftgsledare (utlandsanställda)', '', '', '7232', 'Vinstandelar till tjänstemän och ftgsledare (utlandsanställda)'),
(1001, '', 'Löner till tjänstemän och ftgsledare (utlandsanställda)', '', '', '7237', 'Avgångsvederlag till tjänstemän och ftgsledare (utlandsanställda)'),
(1002, '', 'Löner till tjänstemän och ftgsledare (utlandsanställda)', '', '', '7238', 'Bruttolöneavdrag, tjänstemän och ftgsledare (utlandsanställda)'),
(1003, '', 'Löner till tjänstemän och ftgsledare (utlandsanställda)', '', '', '7239', 'Upplupna löner och vinstandelar till tjänstemän och ftgsledare (utlandsanställda)'),
(1004, '724', 'Styrelsearvoden', '', '1', '7240', 'Styrelsearvoden'),
(1005, '728', 'Löner till tjänstemän och företagsledare för ej arbetad tid', '', '', '7280', 'Löner till tjänstemän och företagsledare för ej arbetad tid'),
(1006, '', 'Löner till tjänstemän och företagsledare för ej arbetad tid', '', '', '7281', 'Sjuklöner till tjänstemän'),
(1007, '', 'Löner till tjänstemän och företagsledare för ej arbetad tid', '', '', '7282', 'Sjuklöner till företagsledare'),
(1008, '', 'Löner till tjänstemän och företagsledare för ej arbetad tid', '', '', '7283', 'Föräldraersättning till tjänstemän'),
(1009, '', 'Löner till tjänstemän och företagsledare för ej arbetad tid', '', '', '7284', 'Föräldraersättning till företagsledare'),
(1010, '', 'Löner till tjänstemän och företagsledare för ej arbetad tid', '', '', '7285', 'Semesterlöner till tjänstemän'),
(1011, '', 'Löner till tjänstemän och företagsledare för ej arbetad tid', '', '', '7286', 'Semesterlöner till företagsledare'),
(1012, '', 'Löner till tjänstemän och företagsledare för ej arbetad tid', '', '', '7288', 'Övriga löner till tjänstemän för ej arbetad tid'),
(1013, '', 'Löner till tjänstemän och företagsledare för ej arbetad tid', '', '', '7289', 'Övriga löner till företagsledare för ej arbetad tid'),
(1014, '729', 'Förändring av semesterlöneskuld', '', '1', '7290', 'Förändring av semesterlöneskuld'),
(1015, '', 'Förändring av semesterlöneskuld', '', '', '7291', 'Förändring av semesterlöneskuld till tjänstemän'),
(1016, '', 'Förändring av semesterlöneskuld', '', '', '7292', 'Förändring av semesterlöneskuld till företagsledare'),
(1017, '73', 'Kostnadsersättningar och förmåner', '', '', '', ''),
(1018, '730', 'Kostnadsersättningar och förmåner (gruppkonto)', '', '', '7300', 'Kostnadsersättningar och förmåner (gruppkonto)'),
(1019, '731', 'Kontanta extraersättningar', '', '1', '7310', 'Kontanta extraersättningar'),
(1020, '', 'Kontanta extraersättningar', '', '', '7311', 'Ersättningar för sammanträden m.m.'),
(1021, '', 'Kontanta extraersättningar', '', '', '7312', 'Ersättningar för förslagsverksamhet och uppfinningar'),
(1022, '', 'Kontanta extraersättningar', '', '', '7313', 'Ersättningar för/bidrag till bostadskostnader'),
(1023, '', 'Kontanta extraersättningar', '', '', '7314', 'Ersättningar för/bidrag till måltidskostnader'),
(1024, '', 'Kontanta extraersättningar', '', '', '7315', 'Ersättningar för/bidrag till resor till och från arbetsplatsen'),
(1025, '', 'Kontanta extraersättningar', '', '', '7316', 'Ersättningar för/bidrag till arbetskläder'),
(1026, '', 'Kontanta extraersättningar', '', '', '7317', 'Ersättningar för/bidrag till arbetsmaterial och arbetsverktyg'),
(1027, '', 'Kontanta extraersättningar', '', '', '7318', 'Felräkningspengar'),
(1028, '', 'Kontanta extraersättningar', '', '', '7319', 'Övriga kontanta extraersättningar'),
(1029, '732', 'Traktamenten vid tjänsteresa', '', '', '7320', 'Traktamenten vid tjänsteresa'),
(1030, '', 'Traktamenten vid tjänsteresa', '', '1', '7321', 'Skattefria traktamenten, Sverige'),
(1031, '', 'Traktamenten vid tjänsteresa', '', '1', '7322', 'Skattepliktiga traktamenten, Sverige'),
(1032, '', 'Traktamenten vid tjänsteresa', '', '1', '7323', 'Skattefria traktamenten, utlandet'),
(1033, '', 'Traktamenten vid tjänsteresa', '', '1', '7324', 'Skattepliktiga traktamenten, utlandet'),
(1034, '733', 'Bilersättningar', '', '', '7330', 'Bilersättningar'),
(1035, '', 'Bilersättningar', '', '1', '7331', 'Skattefria bilersättningar');
INSERT INTO `chart_of_accounts` (`id`, `main_account`, `main_account_description`, `no_k2`, `simple_account`, `sub_account`, `sub_account_description`) VALUES
(1036, '', 'Bilersättningar', '', '1', '7332', 'Skattepliktiga bilersättningar'),
(1037, '', 'Bilersättningar', '', '', '7333', 'Ersättning för trängselskatt, skattefri'),
(1038, '735', 'Ersättningar för föreskrivna arbetskläder', '', '', '7350', 'Ersättningar för föreskrivna arbetskläder'),
(1039, '737', 'Representationsersättningar', '', '', '7370', 'Representationsersättningar'),
(1040, '738', 'Kostnader för förmåner till anställda', '', '1', '7380', 'Kostnader för förmåner till anställda'),
(1041, '', 'Kostnader för förmåner till anställda', '', '', '7381', 'Kostnader för fri bostad'),
(1042, '', 'Kostnader för förmåner till anställda', '', '', '7382', 'Kostnader för fria eller subventionerade måltider'),
(1043, '', 'Kostnader för förmåner till anställda', '', '', '7383', 'Kostnader för fria resor till och från arbetsplatsen'),
(1044, '', 'Kostnader för förmåner till anställda', '', '', '7384', 'Kostnader för fria eller subventionerade arbetskläder'),
(1045, '', 'Kostnader för förmåner till anställda', '', '1', '7385', 'Kostnader för fri bil'),
(1046, '', 'Kostnader för förmåner till anställda', '', '', '7386', 'Subventionerad ränta'),
(1047, '', 'Kostnader för förmåner till anställda', '', '', '7387', 'Kostnader för lånedatorer'),
(1048, '', 'Kostnader för förmåner till anställda', '', '', '7388', 'Anställdas ersättning för erhållna förmåner'),
(1049, '', 'Kostnader för förmåner till anställda', '', '', '7389', 'Övriga kostnader för förmåner'),
(1050, '739', 'Övriga kostnadsersättningar och förmåner', '', '1', '7390', 'Övriga kostnadsersättningar och förmåner'),
(1051, '', 'Övriga kostnadsersättningar och förmåner', '', '', '7391', 'Kostnad för trängselskatteförmån'),
(1052, '', 'Övriga kostnadsersättningar och förmåner', '', '', '7392', 'Kostnad för förmån av hushållsnära tjänster'),
(1053, '74', 'Pensionskostnader', '', '', '', ''),
(1054, '740', 'Pensionskostnader (gruppkonto)', '', '', '7400', 'Pensionskostnader (gruppkonto)'),
(1055, '741', 'Pensionsförsäkringspremier', '', '1', '7410', 'Pensionsförsäkringspremier'),
(1056, '', 'Pensionsförsäkringspremier', '', '', '7411', 'Premier för kollektiva pensionsförsäkringar'),
(1057, '', 'Pensionsförsäkringspremier', '', '', '7412', 'Premier för individuella pensionsförsäkringar'),
(1058, '742', 'Förändring av pensionsskuld', '', '', '7420', 'Förändring av pensionsskuld'),
(1059, '743', 'Avdrag för räntedel i pensionskostnad', '', '', '7430', 'Avdrag för räntedel i pensionskostnad'),
(1060, '744', 'Förändring av pensionsstiftelsekapital', '', '', '7440', 'Förändring av pensionsstiftelsekapital'),
(1061, '', 'Förändring av pensionsstiftelsekapital', '', '', '7441', 'Överföring av medel till pensionsstiftelse'),
(1062, '', 'Förändring av pensionsstiftelsekapital', '', '', '7448', 'Gottgörelse från pensionsstiftelse'),
(1063, '746', 'Pensionsutbetalningar', '', '', '7460', 'Pensionsutbetalningar'),
(1064, '', 'Pensionsutbetalningar', '', '', '7461', 'Pensionsutbetalningar till f.d. kollektivanställda'),
(1065, '', 'Pensionsutbetalningar', '', '', '7462', 'Pensionsutbetalningar till f.d. tjänstemän'),
(1066, '', 'Pensionsutbetalningar', '', '', '7463', 'Pensionsutbetalningar till f.d. företagsledare'),
(1067, '747', 'Förvaltnings- och kreditförsäkringsavgifter', '', '', '7470', 'Förvaltnings- och kreditförsäkringsavgifter'),
(1068, '749', 'Övriga pensionskostnader', '', '1', '7490', 'Övriga pensionskostnader'),
(1069, '75', 'Sociala och andra avgifter enligt lag och avtal', '', '', '', ''),
(1070, '750', 'Sociala och andra avgifter enligt lag och avtal (gruppkonto)', '', '', '7500', 'Sociala och andra avgifter enligt lag och avtal (gruppkonto)'),
(1071, '751', 'Arbetsgivaravgifter 31,42 %', '', '', '7510', 'Arbetsgivaravgifter 31,42 %'),
(1072, '', 'Arbetsgivaravgifter 31,42 %', '', '1', '7511', 'Arbetsgivaravgifter för löner och ersättningar'),
(1073, '', 'Arbetsgivaravgifter 31,42 %', '', '1', '7512', 'Arbetsgivaravgifter för förmånsvärden'),
(1074, '', 'Arbetsgivaravgifter 31,42 %', '', '', '7515', 'Arbetsgivaravgifter på skattepliktiga kostnadsersättningar'),
(1075, '', 'Arbetsgivaravgifter 31,42 %', '', '', '7516', 'Arbetsgivaravgifter på arvoden'),
(1076, '', 'Arbetsgivaravgifter 31,42 %', '', '', '7518', 'Arbetsgivaravgifter på bruttolöneavdrag m.m.'),
(1077, '', 'Arbetsgivaravgifter 31,42 %', '', '1', '7519', 'Arbetsgivaravgifter för semester- och löneskulder'),
(1078, '753', 'Särskild löneskatt', '', '1', '7530', 'Särskild löneskatt'),
(1079, '', 'Särskild löneskatt', '', '', '7531', 'Särskild löneskatt för vissa försäkringsersättningar m.m.'),
(1080, '', 'Särskild löneskatt', '', '', '7532', 'Särskild löneskatt pensionskostnader, deklarationspost'),
(1081, '', 'Särskild löneskatt', '', '', '7533', 'Särskild löneskatt för pensionskostnader'),
(1082, '755', 'Avkastningsskatt på pensionsmedel', '', '1', '7550', 'Avkastningsskatt på pensionsmedel'),
(1083, '', 'Avkastningsskatt på pensionsmedel', '', '', '7551', 'Avkastningsskatt 15 % försäkringsföretag m.fl. samt avsatt till pensioner'),
(1084, '', 'Avkastningsskatt på pensionsmedel', '', '', '7552', 'Avkastningsskatt 15 % utländska pensionsförsäkringar'),
(1085, '', 'Avkastningsskatt på pensionsmedel', '', '', '7553', 'Avkastningsskatt 30 % utländska försäkringsföretag m.fl.'),
(1086, '', 'Avkastningsskatt på pensionsmedel', '', '', '7554', 'Avkastningsskatt 30 % utländska kapitalförsäkringar'),
(1087, '757', 'Premier för arbetsmarknadsförsäkringar', '', '1', '7570', 'Premier för arbetsmarknadsförsäkringar'),
(1088, '', 'Premier för arbetsmarknadsförsäkringar', '', '', '7571', 'Arbetsmarknadsförsäkringar'),
(1089, '', 'Premier för arbetsmarknadsförsäkringar', '', '', '7572', 'Arbetsmarknadsförsäkringar pensionsförsäkringspremier, deklarationspost'),
(1090, '758', 'Gruppförsäkringspremier', '', '1', '7580', 'Gruppförsäkringspremier'),
(1091, '', 'Gruppförsäkringspremier', '', '', '7581', 'Grupplivförsäkringspremier'),
(1092, '', 'Gruppförsäkringspremier', '', '', '7582', 'Gruppsjukförsäkringspremier'),
(1093, '', 'Gruppförsäkringspremier', '', '', '7583', 'Gruppolycksfallsförsäkringspremier'),
(1094, '', 'Gruppförsäkringspremier', '', '', '7589', 'Övriga gruppförsäkringspremier'),
(1095, '759', 'Övriga sociala och andra avgifter enligt lag och avtal', '', '1', '7590', 'Övriga sociala och andra avgifter enligt lag och avtal'),
(1096, '76', 'Övriga personalkostnader', '', '', '', ''),
(1097, '760', 'Övriga personalkostnader (gruppkonto)', '', '1', '7600', 'Övriga personalkostnader (gruppkonto)'),
(1098, '761', 'Utbildning', '', '1', '7610', 'Utbildning'),
(1099, '762', 'Sjuk- och hälsovård', '', '', '7620', 'Sjuk- och hälsovård'),
(1100, '', 'Sjuk- och hälsovård', '', '1', '7621', 'Sjuk- och hälsovård, avdragsgill'),
(1101, '', 'Sjuk- och hälsovård', '', '1', '7622', 'Sjuk- och hälsovård, ej avdragsgill'),
(1102, '', 'Sjuk- och hälsovård', '', '', '7623', 'Sjukvårdsförsäkring, ej avdragsgill'),
(1103, '763', 'Personalrepresentation', '', '', '7630', 'Personalrepresentation'),
(1104, '', 'Personalrepresentation', '', '1', '7631', 'Personalrepresentation, avdragsgill'),
(1105, '', 'Personalrepresentation', '', '1', '7632', 'Personalrepresentation, ej avdragsgill'),
(1106, '765', 'Sjuklöneförsäkring', '', '', '7650', 'Sjuklöneförsäkring'),
(1107, '767', 'Förändring av personalstiftelsekapital', '', '', '7670', 'Förändring av personalstiftelsekapital'),
(1108, '', 'Förändring av personalstiftelsekapital', '', '', '7671', 'Avsättning till personalstiftelse'),
(1109, '', 'Förändring av personalstiftelsekapital', '', '', '7678', 'Gottgörelse från personalstiftelse'),
(1110, '769', 'Övriga personalkostnader', '', '', '7690', 'Övriga personalkostnader'),
(1111, '', 'Övriga personalkostnader', '', '', '7691', 'Personalrekrytering'),
(1112, '', 'Övriga personalkostnader', '', '', '7692', 'Begravningshjälp'),
(1113, '', 'Övriga personalkostnader', '', '', '7693', 'Fritidsverksamhet'),
(1114, '', 'Övriga personalkostnader', '', '', '7699', 'Övriga personalkostnader'),
(1115, '77', 'Nedskrivningar och återföring av nedskrivningar', '', '', '', ''),
(1116, '771', 'Nedskrivningar av immateriella anläggningstillgångar', '', '', '7710', 'Nedskrivningar av immateriella anläggningstillgångar'),
(1117, '772', 'Nedskrivningar av byggnader och mark', '', '1', '7720', 'Nedskrivningar av byggnader och mark'),
(1118, '773', 'Nedskrivningar av maskiner och inventarier', '', '1', '7730', 'Nedskrivningar av maskiner och inventarier'),
(1119, '774', 'Nedskrivningar av vissa omsättningstillgångar', '', '', '7740', 'Nedskrivningar av vissa omsättningstillgångar'),
(1120, '776', 'Återföring av nedskrivningar av immateriella anläggningstillgångar', '', '', '7760', 'Återföring av nedskrivningar av immateriella anläggningstillgångar'),
(1121, '777', 'Återföring av nedskrivningar av byggnader och mark', '', '', '7770', 'Återföring av nedskrivningar av byggnader och mark'),
(1122, '778', 'Återföring av nedskrivningar av maskiner och inventarier', '', '', '7780', 'Återföring av nedskrivningar av maskiner och inventarier'),
(1123, '779', 'Återföring av nedskrivningar av vissa omsättningstillgångar', '', '', '7790', 'Återföring av nedskrivningar av vissa omsättningstillgångar'),
(1124, '78', 'Avskrivningar enligt plan', '', '', '', ''),
(1125, '781', 'Avskrivningar på immateriella anläggningstillgångar', '', '1', '7810', 'Avskrivningar på immateriella anläggningstillgångar'),
(1126, '', 'Avskrivningar på immateriella anläggningstillgångar', '', '', '7811', 'Avskrivningar på balanserade utgifter'),
(1127, '', 'Avskrivningar på immateriella anläggningstillgångar', '', '', '7812', 'Avskrivningar på koncessioner m.m.'),
(1128, '', 'Avskrivningar på immateriella anläggningstillgångar', '', '', '7813', 'Avskrivningar på patent'),
(1129, '', 'Avskrivningar på immateriella anläggningstillgångar', '', '', '7814', 'Avskrivningar på licenser'),
(1130, '', 'Avskrivningar på immateriella anläggningstillgångar', '', '', '7815', 'Avskrivningar på varumärken'),
(1131, '', 'Avskrivningar på immateriella anläggningstillgångar', '', '', '7816', 'Avskrivningar på hyresrätter'),
(1132, '', 'Avskrivningar på immateriella anläggningstillgångar', '', '', '7817', 'Avskrivningar på goodwill'),
(1133, '', 'Avskrivningar på immateriella anläggningstillgångar', '', '', '7819', 'Avskrivningar på övriga immateriella anläggningstillgångar'),
(1134, '782', 'Avskrivningar på byggnader och markanläggningar', '', '1', '7820', 'Avskrivningar på byggnader och markanläggningar'),
(1135, '', 'Avskrivningar på byggnader och markanläggningar', '', '', '7821', 'Avskrivningar på byggnader'),
(1136, '', 'Avskrivningar på byggnader och markanläggningar', '', '', '7824', 'Avskrivningar på markanläggningar'),
(1137, '', 'Avskrivningar på byggnader och markanläggningar', '', '', '7829', 'Avskrivningar på övriga byggnader'),
(1138, '783', 'Avskrivningar på maskiner och inventarier', '', '1', '7830', 'Avskrivningar på maskiner och inventarier'),
(1139, '', 'Avskrivningar på maskiner och inventarier', '', '', '7831', 'Avskrivningar på maskiner och andra tekniska anläggningar'),
(1140, '', 'Avskrivningar på maskiner och inventarier', '', '', '7832', 'Avskrivningar på inventarier och verktyg'),
(1141, '', 'Avskrivningar på maskiner och inventarier', '', '', '7833', 'Avskrivningar på installationer'),
(1142, '', 'Avskrivningar på maskiner och inventarier', '', '', '7834', 'Avskrivningar på bilar och andra transportmedel'),
(1143, '', 'Avskrivningar på maskiner och inventarier', '', '', '7835', 'Avskrivningar på datorer'),
(1144, '', 'Avskrivningar på maskiner och inventarier', '', '', '7836', 'Avskrivningar på leasade tillgångar'),
(1145, '', 'Avskrivningar på maskiner och inventarier', '', '', '7839', 'Avskrivningar på övriga maskiner och inventarier'),
(1146, '784', 'Avskrivningar på förbättringsutgifter på annans fastighet', '', '', '7840', 'Avskrivningar på förbättringsutgifter på annans fastighet'),
(1147, '79', 'Övriga rörelsekostnader', '', '', '', ''),
(1148, '794', 'Orealiserade positiva/negativa värdeförändringar på säkringsinstrument', '1', '', '7940', 'Orealiserade positiva/negativa värdeförändringar på säkringsinstrument'),
(1149, '796', 'Valutakursförluster på fordringar och skulder av rörelsekaraktär', '', '', '7960', 'Valutakursförluster på fordringar och skulder av rörelsekaraktär'),
(1150, '797', 'Förlust vid avyttring av immateriella och materiella anläggningstillgångar', '', '1', '7970', 'Förlust vid avyttring av immateriella och materiella anläggningstillgångar'),
(1151, '', 'Förlust vid avyttring av immateriella och materiella anläggningstillgångar', '', '', '7971', 'Förlust vid avyttring av immateriella anläggningstillgångar'),
(1152, '', 'Förlust vid avyttring av immateriella och materiella anläggningstillgångar', '', '', '7972', 'Förlust vid avyttring av byggnader och mark'),
(1153, '', 'Förlust vid avyttring av immateriella och materiella anläggningstillgångar', '', '', '7973', 'Förlust vid avyttring av maskiner och inventarier'),
(1154, '799', 'Övriga rörelsekostnader', '', '1', '7990', 'Övriga rörelsekostnader'),
(1155, '8', 'Finansiella och andra inkomster/ intäkter och utgifter/kostnader', '', '', '', ''),
(1156, '80', 'Resultat från andelar i koncernföretag', '', '', '', ''),
(1157, '801', 'Utdelning på andelar i koncernföretag', '', '', '8010', 'Utdelning på andelar i koncernföretag'),
(1158, '', 'Utdelning på andelar i koncernföretag', '', '', '8012', 'Utdelning på andelar i dotterföretag'),
(1159, '', 'Utdelning på andelar i koncernföretag', '', '', '8016', 'Emissionsinsats, koncernföretag'),
(1160, '802', 'Resultat vid försäljning av andelar i koncernföretag', '', '', '8020', 'Resultat vid försäljning av andelar i koncernföretag'),
(1161, '', 'Resultat vid försäljning av andelar i koncernföretag', '', '', '8022', 'Resultat vid försäljning av andelar i dotterföretag'),
(1162, '803', 'Resultatandelar från handelsbolag (dotterföretag)', '', '', '8030', 'Resultatandelar från handelsbolag (dotterföretag)'),
(1163, '807', 'Nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', '', '', '8070', 'Nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag'),
(1164, '', 'Nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', '', '', '8072', 'Nedskrivningar av andelar i dotterföretag'),
(1165, '', 'Nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', '', '', '8076', 'Nedskrivningar av långfristiga fordringar hos moderföretag'),
(1166, '', 'Nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', '', '', '8077', 'Nedskrivningar av långfristiga fordringar hos dotterföretag'),
(1167, '808', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', '', '', '8080', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag'),
(1168, '', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', '', '', '8082', 'Återföringar av nedskrivningar av andelar i dotterföretag'),
(1169, '', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', '', '', '8086', 'Återföringar av nedskrivningar av långfristiga fordringar hos moderföretag'),
(1170, '', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos koncernföretag', '', '', '8087', 'Återföringar av nedskrivningar av långfristiga fordringar hos dotterföretag'),
(1171, '81', 'Resultat från andelar i intresseföretag', '', '', '', ''),
(1172, '811', 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8110', 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(1173, '', 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8111', 'Utdelningar på andelar i intresseföretag'),
(1174, '', 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8112', 'Utdelningar på andelar i gemensamt styrda företag'),
(1175, '', 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8113', 'Utdelningar på andelar i övriga företag som det finns ett ägarintresse i'),
(1176, '', 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8116', 'Emissionsinsats, intresseföretag'),
(1177, '', 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8117', 'Emissionsinsats, gemensamt styrda företag'),
(1178, '', 'Utdelningar på andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8118', 'Emissionsinsats, övriga företag som det finns ett ägarintresse i'),
(1179, '812', 'Resultat vid försäljning av andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8120', 'Resultat vid försäljning av andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(1180, '', 'Resultat vid försäljning av andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8121', 'Resultat vid försäljning av andelar i intresseföretag'),
(1181, '', 'Resultat vid försäljning av andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8122', 'Resultat vid försäljning av andelar i gemensamt styrda företag'),
(1182, '', 'Resultat vid försäljning av andelar i intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8123', 'Resultat vid försäljning av andelar i övriga företag som det finns ett ägarintresse i'),
(1183, '813', 'Resultatandelar från handelsbolag (intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i)', '', '', '8130', 'Resultatandelar från handelsbolag (intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i)'),
(1184, '', 'Resultatandelar från handelsbolag (intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i)', '', '', '8131', 'Resultatandelar från handelsbolag (intresseföretag)'),
(1185, '', 'Resultatandelar från handelsbolag (intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i)', '', '', '8132', 'Resultatandelar från handelsbolag (gemensamt styrda företag)'),
(1186, '', 'Resultatandelar från handelsbolag (intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i)', '', '', '8133', 'Resultatandelar från handelsbolag (övriga företag som det finns ett ägarintresse i)'),
(1187, '817', 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8170', 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i'),
(1188, '', 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8171', 'Nedskrivningar av andelar i intresseföretag'),
(1189, '', 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8172', 'Nedskrivningar av långfristiga fordringar hos intresseföretag'),
(1190, '', 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8173', 'Nedskrivningar av andelar i gemensamt styrda företag'),
(1191, '', 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8174', 'Nedskrivningar av långfristiga fordringar hos gemensamt styrda företag'),
(1192, '', 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8176', 'Nedskrivningar av andelar i övriga företag som det finns ett ägarintresse i'),
(1193, '', 'Nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag, gemensamt styrda företag och övriga företag som det finns ett ägarintresse i', '', '', '8177', 'Nedskrivningar av långfristiga fordringar hos övriga företag som det finns ett ägarintresse i'),
(1194, '818', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag', '', '', '8180', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag'),
(1195, '', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag', '', '', '8181', 'Återföringar av nedskrivningar av andelar i intresseföretag'),
(1196, '', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag', '', '', '8182', 'Återföringar av nedskrivningar av långfristiga fordringar hos intresseföretag'),
(1197, '', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag', '', '', '8183', 'Återföringar av nedskrivningar av andelar i gemensamt styrda företag'),
(1198, '', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag', '', '', '8184', 'Återföringar av nedskrivningar av långfristiga fordringar hos gemensamt styrda företag'),
(1199, '', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag', '', '', '8186', 'Återföringar av nedskrivningar av andelar i övriga företag som det finns ett ägarintresse i'),
(1200, '', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos intresseföretag', '', '', '8187', 'Återföringar av nedskrivningar av långfristiga fordringar hos övriga företag som det finns ett ägarintresse i'),
(1201, '82', 'Resultat från övriga värdepapper och långfristiga fordringar (anläggningstillgångar)', '', '', '', ''),
(1202, '821', 'Utdelningar på andelar i andra företag', '', '1', '8210', 'Utdelningar på andelar i andra företag'),
(1203, '', 'Utdelningar på andelar i andra företag', '', '', '8212', 'Utdelningar, övriga företag'),
(1204, '', 'Utdelningar på andelar i andra företag', '', '', '8216', 'Insatsemissioner, övriga företag'),
(1205, '822', 'Resultat vid försäljning av värdepapper i och långfristiga fordringar hos andra företag', '', '1', '8220', 'Resultat vid försäljning av värdepapper i och långfristiga fordringar hos andra företag'),
(1206, '', 'Resultat vid försäljning av värdepapper i och långfristiga fordringar hos andra företag', '', '', '8221', 'Resultat vid försäljning av andelar i andra företag'),
(1207, '', 'Resultat vid försäljning av värdepapper i och långfristiga fordringar hos andra företag', '', '', '8222', 'Resultat vid försäljning av långfristiga fordringar hos andra företag'),
(1208, '', 'Resultat vid försäljning av värdepapper i och långfristiga fordringar hos andra företag', '', '', '8223', 'Resultat vid försäljning av derivat (långfristiga värdepappersinnehav)'),
(1209, '823', 'Valutakursdifferenser på långfristiga fordringar', '', '', '8230', 'Valutakursdifferenser på långfristiga fordringar'),
(1210, '', 'Valutakursdifferenser på långfristiga fordringar', '', '', '8231', 'Valutakursvinster på långfristiga fordringar'),
(1211, '', 'Valutakursdifferenser på långfristiga fordringar', '', '', '8236', 'Valutakursförluster på långfristiga fordringar'),
(1212, '824', 'Resultatandelar från handelsbolag (andra företag)', '', '', '8240', 'Resultatandelar från handelsbolag (andra företag)'),
(1213, '825', 'Ränteintäkter från långfristiga fordringar hos och värdepapper i andra företag', '', '1', '8250', 'Ränteintäkter från långfristiga fordringar hos och värdepapper i andra företag'),
(1214, '', 'Ränteintäkter från långfristiga fordringar hos och värdepapper i andra företag', '', '', '8251', 'Ränteintäkter från långfristiga fordringar'),
(1215, '', 'Ränteintäkter från långfristiga fordringar hos och värdepapper i andra företag', '', '', '8252', 'Ränteintäkter från övriga värdepapper'),
(1216, '', 'Ränteintäkter från långfristiga fordringar hos och värdepapper i andra företag', '', '', '8254', 'Skattefria ränteintäkter, långfristiga tillgångar'),
(1217, '', 'Ränteintäkter från långfristiga fordringar hos och värdepapper i andra företag', '', '', '8255', 'Avkastningsskatt kapitalplacering'),
(1218, '826', 'Ränteintäkter från långfristiga fordringar hos koncernföretag', '', '', '8260', 'Ränteintäkter från långfristiga fordringar hos koncernföretag'),
(1219, '', 'Ränteintäkter från långfristiga fordringar hos koncernföretag', '', '', '8261', 'Ränteintäkter från långfristiga fordringar hos moderföretag'),
(1220, '', 'Ränteintäkter från långfristiga fordringar hos koncernföretag', '', '', '8262', 'Ränteintäkter från långfristiga fordringar hos dotterföretag'),
(1221, '', 'Ränteintäkter från långfristiga fordringar hos koncernföretag', '', '', '8263', 'Ränteintäkter från långfristiga fordringar hos andra koncernföretag'),
(1222, '827', 'Nedskrivningar av innehav av andelar i och långfristiga fordringar hos andra företag', '', '1', '8270', 'Nedskrivningar av innehav av andelar i och långfristiga fordringar hos andra företag'),
(1223, '', 'Nedskrivningar av innehav av andelar i och långfristiga fordringar hos andra företag', '', '', '8271', 'Nedskrivningar av andelar i andra företag'),
(1224, '', 'Nedskrivningar av innehav av andelar i och långfristiga fordringar hos andra företag', '', '', '8272', 'Nedskrivningar av långfristiga fordringar hos andra företag'),
(1225, '', 'Nedskrivningar av innehav av andelar i och långfristiga fordringar hos andra företag', '', '', '8273', 'Nedskrivningar av övriga värdepapper hos andra företag'),
(1226, '828', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos andra företag', '', '', '8280', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos andra företag'),
(1227, '', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos andra företag', '', '', '8281', 'Återföringar av nedskrivningar av andelar i andra företag'),
(1228, '', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos andra företag', '', '', '8282', 'Återföringar av nedskrivningar av långfristiga fordringar hos andra företag'),
(1229, '', 'Återföringar av nedskrivningar av andelar i och långfristiga fordringar hos andra företag', '', '', '8283', 'Återföringar av nedskrivningar av övriga värdepapper i andra företag'),
(1230, '829', 'Värdering till verkligt värde, anläggningstillgångar', '1', '', '8290', 'Värdering till verkligt värde, anläggningstillgångar'),
(1231, '', 'Värdering till verkligt värde, anläggningstillgångar', '1', '', '8291', 'Orealiserade värdeförändringar på anläggningstillgångar'),
(1232, '', 'Värdering till verkligt värde, anläggningstillgångar', '1', '', '8295', 'Orealiserade värdeförändringar på derivatinstrument'),
(1233, '83', 'Övriga ränteintäkter och liknande resultatposter', '', '', '', ''),
(1234, '831', 'Ränteintäkter från omsättningstillgångar', '', '1', '8310', 'Ränteintäkter från omsättningstillgångar'),
(1235, '', 'Ränteintäkter från omsättningstillgångar', '', '', '8311', 'Ränteintäkter från bank'),
(1236, '', 'Ränteintäkter från omsättningstillgångar', '', '', '8312', 'Ränteintäkter från kortfristiga placeringar'),
(1237, '', 'Ränteintäkter från omsättningstillgångar', '', '', '8313', 'Ränteintäkter från kortfristiga fordringar'),
(1238, '', 'Ränteintäkter från omsättningstillgångar', '', '1', '8314', 'Skattefria ränteintäkter'),
(1239, '', 'Ränteintäkter från omsättningstillgångar', '', '', '8317', 'Ränteintäkter för dold räntekompensation'),
(1240, '', 'Ränteintäkter från omsättningstillgångar', '', '', '8319', 'Övriga ränteintäkter från omsättningstillgångar'),
(1241, '832', 'Värdering till verkligt värde, omsättningstillgångar', '1', '', '8320', 'Värdering till verkligt värde, omsättningstillgångar'),
(1242, '', 'Värdering till verkligt värde, omsättningstillgångar', '1', '', '8321', 'Orealiserade värdeförändringar på omsättningstillgångar'),
(1243, '', 'Värdering till verkligt värde, omsättningstillgångar', '1', '', '8325', 'Orealiserade värdeförändringar på derivatinstrument (oms.-tillg.)'),
(1244, '833', 'Valutakursdifferenser på kortfristiga fordringar och placeringar', '', '1', '8330', 'Valutakursdifferenser på kortfristiga fordringar och placeringar'),
(1245, '', 'Valutakursdifferenser på kortfristiga fordringar och placeringar', '', '', '8331', 'Valutakursvinster på kortfristiga fordringar och placeringar'),
(1246, '', 'Valutakursdifferenser på kortfristiga fordringar och placeringar', '', '', '8336', 'Valutakursförluster på kortfristiga fordringar och placeringar'),
(1247, '834', 'Utdelningar på kortfristiga placeringar', '', '1', '8340', 'Utdelningar på kortfristiga placeringar'),
(1248, '835', 'Resultat vid försäljning av kortfristiga placeringar', '', '1', '8350', 'Resultat vid försäljning av kortfristiga placeringar'),
(1249, '836', 'Övriga ränteintäkter från koncernföretag', '', '', '8360', 'Övriga ränteintäkter från koncernföretag'),
(1250, '', 'Övriga ränteintäkter från koncernföretag', '', '', '8361', 'Övriga ränteintäkter från moderföretag'),
(1251, '', 'Övriga ränteintäkter från koncernföretag', '', '', '8362', 'Övriga ränteintäkter från dotterföretag'),
(1252, '', 'Övriga ränteintäkter från koncernföretag', '', '', '8363', 'Övriga ränteintäkter från andra koncernföretag'),
(1253, '837', 'Nedskrivningar av kortfristiga placeringar', '', '', '8370', 'Nedskrivningar av kortfristiga placeringar'),
(1254, '838', 'Återföringar av nedskrivningar av kortfristiga placeringar', '', '', '8380', 'Återföringar av nedskrivningar av kortfristiga placeringar'),
(1255, '839', 'Övriga finansiella intäkter', '', '1', '8390', 'Övriga finansiella intäkter'),
(1256, '84', 'Räntekostnader och liknande resultatposter', '', '', '', ''),
(1257, '840', 'Räntekostnader (gruppkonto)', '', '', '8400', 'Räntekostnader (gruppkonto)'),
(1258, '841', 'Räntekostnader för långfristiga skulder', '', '1', '8410', 'Räntekostnader för långfristiga skulder'),
(1259, '', 'Räntekostnader för långfristiga skulder', '', '', '8411', 'Räntekostnader för obligations-, förlags- och konvertibla lån'),
(1260, '', 'Räntekostnader för långfristiga skulder', '', '', '8412', 'Räntedel i årets pensionskostnad'),
(1261, '', 'Räntekostnader för långfristiga skulder', '', '', '8413', 'Räntekostnader för checkräkningskredit'),
(1262, '', 'Räntekostnader för långfristiga skulder', '', '', '8415', 'Räntekostnader för andra skulder till kreditinstitut'),
(1263, '', 'Räntekostnader för långfristiga skulder', '1', '', '8417', 'Räntekostnader för dold räntekompensation m.m.'),
(1264, '', 'Räntekostnader för långfristiga skulder', '', '', '8418', 'Avdragspost för räntesubventioner'),
(1265, '', 'Räntekostnader för långfristiga skulder', '', '', '8419', 'Övriga räntekostnader för långfristiga skulder'),
(1266, '842', 'Räntekostnader för kortfristiga skulder', '', '1', '8420', 'Räntekostnader för kortfristiga skulder'),
(1267, '', 'Räntekostnader för kortfristiga skulder', '', '', '8421', 'Räntekostnader till kreditinstitut'),
(1268, '', 'Räntekostnader för kortfristiga skulder', '', '1', '8422', 'Dröjsmålsräntor för leverantörsskulder'),
(1269, '', 'Räntekostnader för kortfristiga skulder', '', '1', '8423', 'Räntekostnader för skatter och avgifter'),
(1270, '', 'Räntekostnader för kortfristiga skulder', '', '', '8424', 'Räntekostnader byggnadskreditiv'),
(1271, '', 'Räntekostnader för kortfristiga skulder', '', '', '8429', 'Övriga räntekostnader för kortfristiga skulder'),
(1272, '843', 'Valutakursdifferenser på skulder', '', '1', '8430', 'Valutakursdifferenser på skulder'),
(1273, '', 'Valutakursdifferenser på skulder', '', '', '8431', 'Valutakursvinster på skulder'),
(1274, '', 'Valutakursdifferenser på skulder', '', '', '8436', 'Valutakursförluster på skulder'),
(1275, '844', 'Erhållna räntebidrag', '', '', '8440', 'Erhållna räntebidrag'),
(1276, '845', 'Orealiserade värdeförändringar på skulder', '1', '', '8450', 'Orealiserade värdeförändringar på skulder'),
(1277, '', 'Orealiserade värdeförändringar på skulder', '1', '', '8451', 'Orealiserade värdeförändringar på skulder'),
(1278, '', 'Orealiserade värdeförändringar på skulder', '1', '', '8455', 'Orealiserade värdeförändringar på säkringsinstrument'),
(1279, '846', 'Räntekostnader till koncernföretag', '', '', '8460', 'Räntekostnader till koncernföretag'),
(1280, '', 'Räntekostnader till koncernföretag', '', '', '8461', 'Räntekostnader till moderföretag'),
(1281, '', 'Räntekostnader till koncernföretag', '', '', '8462', 'Räntekostnader till dotterföretag'),
(1282, '', 'Räntekostnader till koncernföretag', '', '', '8463', 'Räntekostnader till andra koncernföretag'),
(1283, '848', 'Aktiverade ränteutgifter', '1', '', '8480', 'Aktiverade ränteutgifter'),
(1284, '849', 'Övriga skuldrelaterade poster', '', '', '8490', 'Övriga skuldrelaterade poster'),
(1285, '', 'Övriga skuldrelaterade poster', '', '', '8491', 'Erhållet ackord på skulder till kreditinstitut m.m.'),
(1286, '85', '(Fri kontogrupp)', '', '', '', ''),
(1287, '86', '(Fri kontogrupp)', '', '', '', ''),
(1288, '87', '(Fri kontogrupp)', '', '', '', ''),
(1289, '88', 'Bokslutsdispositioner', '', '', '', ''),
(1290, '881', 'Förändring av periodiseringsfond', '', '', '8810', 'Förändring av periodiseringsfond'),
(1291, '', '', '', '1', '8811', 'Avsättning till periodiseringsfond'),
(1292, '', '', '', '1', '8819', 'Återföring från periodiseringsfond'),
(1293, '882', 'Mottagna koncernbidrag', '', '', '8820', 'Mottagna koncernbidrag'),
(1294, '883', 'Lämnade koncernbidrag', '', '', '8830', 'Lämnade koncernbidrag'),
(1295, '884', 'Lämnade gottgörelser', '', '', '8840', 'Lämnade gottgörelser'),
(1296, '885', 'Förändring av överavskrivningar', '', '1', '8850', 'Förändring av överavskrivningar'),
(1297, '', 'Förändring av överavskrivningar', '', '', '8851', 'Förändring av överavskrivningar, immateriella anläggningstillgångar'),
(1298, '', 'Förändring av överavskrivningar', '', '', '8852', 'Förändring av överavskrivningar, byggnader och markanläggningar'),
(1299, '', 'Förändring av överavskrivningar', '', '', '8853', 'Förändring av överavskrivningar, maskiner och inventarier'),
(1300, '886', 'Förändring av ersättningsfond', '', '', '8860', 'Förändring av ersättningsfond'),
(1301, '', 'Förändring av ersättningsfond', '', '', '8861', 'Avsättning till ersättningsfond för inventarier'),
(1302, '', 'Förändring av ersättningsfond', '', '', '8862', 'Avsättning till ersättningsfond för byggnader och markanläggningar'),
(1303, '', 'Förändring av ersättningsfond', '', '', '8864', 'Avsättning till ersättningsfond för djurlager i jordbruk och renskötsel'),
(1304, '', 'Förändring av ersättningsfond', '', '', '8865', 'Ianspråktagande av ersättningsfond för avskrivningar'),
(1305, '', 'Förändring av ersättningsfond', '', '', '8866', 'Ianspråktagande av ersättningsfond för annat än avskrivningar'),
(1306, '', 'Förändring av ersättningsfond', '', '', '8869', 'Återföring från ersättningsfond'),
(1307, '889', 'Övriga bokslutsdispositioner', '', '', '8890', 'Övriga bokslutsdispositioner'),
(1308, '', 'Övriga bokslutsdispositioner', '', '', '8892', 'Nedskrivningar av konsolideringskaraktär av anläggningstillgångar'),
(1309, '', 'Övriga bokslutsdispositioner', '', '', '8896', 'Förändring av lagerreserv'),
(1310, '', 'Övriga bokslutsdispositioner', '', '', '8899', 'Övriga bokslutsdispositioner'),
(1311, '89', 'Skatter och årets resultat', '', '', '', ''),
(1312, '891', 'Skatt på grund av ändrad beskattning', '', '1', '8910', 'Skatt som belastar årets resultat'),
(1313, '892', 'Skatt som belastar årets resultat', '', '', '8920', 'Skatt på grund av ändrad beskattning'),
(1314, '893', 'Restituerad skatt', '', '', '8930', 'Restituerad skatt'),
(1315, '894', 'Uppskjuten skatt', '1', '', '8940', 'Uppskjuten skatt'),
(1316, '898', 'Övriga skatter', '', '', '8980', 'Övriga skatter'),
(1317, '899', 'Resultat', '', '1', '8990', 'Resultat'),
(1318, '', '', '', '1', '8999', 'Årets resultat');

-- --------------------------------------------------------

--
-- Tabellstruktur `companies`
--

CREATE TABLE `companies` (
  `id` int NOT NULL,
  `name` varchar(234) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'The name of the company',
  `orgnr` varchar(22) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'The company organization number. ',
  `address` int NOT NULL COMMENT 'Street address',
  `address2` varchar(222) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'Extra addres row',
  `zip` varchar(123) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'Zip-code',
  `city` varchar(234) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'City of the company',
  `country` varchar(234) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'Country of the company',
  `phone` varchar(234) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'Phone number to company',
  `www` varchar(234) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'Company homepage'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Tabellstruktur `creditcard_invoices_main`
--

CREATE TABLE `creditcard_invoices_main` (
  `id` bigint UNSIGNED NOT NULL COMMENT 'Primary key, internal unique ID',
  `invoice_number` varchar(50) COLLATE utf8mb4_swedish_ci NOT NULL COMMENT 'Invoice number as provided by the issuer',
  `invoice_print_time` datetime DEFAULT NULL COMMENT 'Exact print or generation time of the invoice',
  `card_type` varchar(50) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Type of card (e.g., Visa, MasterCard)',
  `card_name` varchar(100) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Name of card product (e.g., Company Card)',
  `card_number_masked` varchar(32) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Masked card number, usually ****1234',
  `card_holder` varchar(100) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Name of the card holder',
  `cost_center` varchar(100) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Cost center associated with the card',
  `customer_name` varchar(150) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Customer or company name on invoice',
  `co` varchar(150) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Optional C/O or attention line',
  `address` text COLLATE utf8mb4_swedish_ci COMMENT 'Full postal address',
  `bank_name` varchar(100) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Name of issuing bank',
  `bank_org_no` varchar(50) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Bank organization number',
  `bank_vat_no` varchar(50) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Bank VAT registration number',
  `bank_fi_no` varchar(50) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Bank FI number or license reference',
  `invoice_date` date DEFAULT NULL COMMENT 'Date of invoice',
  `customer_number` varchar(50) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Customer number at the card company',
  `invoice_number_long` varchar(100) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Alternative or full-length invoice number',
  `due_date` date DEFAULT NULL COMMENT 'Payment due date',
  `invoice_total` decimal(13,2) DEFAULT NULL COMMENT 'Total amount on invoice (may include fees)',
  `payment_plusgiro` varchar(30) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'PlusGiro number for payment',
  `payment_bankgiro` varchar(30) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'BankGiro number for payment',
  `payment_iban` varchar(34) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'IBAN for international payment',
  `payment_bic` varchar(11) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'BIC/SWIFT code',
  `payment_ocr` varchar(50) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'OCR number/reference for payment',
  `payment_due` date DEFAULT NULL COMMENT 'Due date from payment section',
  `card_total` decimal(13,2) DEFAULT NULL COMMENT 'Total charges on all cards for this invoice',
  `sum` decimal(13,2) DEFAULT NULL COMMENT 'Summary amount (as printed)',
  `vat_25` decimal(13,2) DEFAULT NULL COMMENT 'VAT amount at 25%',
  `vat_12` decimal(13,2) DEFAULT NULL COMMENT 'VAT amount at 12%',
  `vat_6` decimal(13,2) DEFAULT NULL COMMENT 'VAT amount at 6%',
  `vat_0` decimal(13,2) DEFAULT NULL COMMENT 'VAT amount at 0% (exempt)',
  `amount_to_pay` decimal(13,2) DEFAULT NULL COMMENT 'Final amount to pay',
  `reported_vat` decimal(13,2) DEFAULT NULL COMMENT 'Total VAT reported on invoice',
  `next_invoice` date DEFAULT NULL COMMENT 'Expected date of next invoice',
  `note_1` text COLLATE utf8mb4_swedish_ci COMMENT 'Internal note 1',
  `note_2` text COLLATE utf8mb4_swedish_ci COMMENT 'Internal note 2',
  `note_3` text COLLATE utf8mb4_swedish_ci COMMENT 'Internal note 3',
  `note_4` text COLLATE utf8mb4_swedish_ci COMMENT 'Internal note 4',
  `note_5` text COLLATE utf8mb4_swedish_ci COMMENT 'Internal note 5'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_swedish_ci COMMENT='Main credit-card invoice table, one row per monthly invoice';

-- --------------------------------------------------------

--
-- Tabellstruktur `creditcard_invoice_items`
--

CREATE TABLE `creditcard_invoice_items` (
  `id` bigint UNSIGNED NOT NULL COMMENT 'Primary key, internal unique ID',
  `main_id` bigint UNSIGNED NOT NULL COMMENT 'FK to creditcard_invoices_main.id',
  `line_no` int NOT NULL COMMENT 'Line number within invoice (1..N)',
  `transaction_id` varchar(64) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Transaction reference from issuer',
  `purchase_date` date DEFAULT NULL COMMENT 'Date purchase occurred',
  `posting_date` date DEFAULT NULL COMMENT 'Date transaction was posted',
  `merchant_name` varchar(200) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Name of merchant/vendor',
  `merchant_city` varchar(100) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'City of merchant',
  `merchant_country` char(2) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'ISO 3166-1 alpha-2 country code',
  `mcc` varchar(4) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Merchant Category Code',
  `description` text COLLATE utf8mb4_swedish_ci COMMENT 'Free-text transaction description',
  `currency_original` char(3) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Original currency code (ISO 4217)',
  `amount_original` decimal(13,2) DEFAULT NULL COMMENT 'Original amount in currency_original',
  `exchange_rate` decimal(18,6) DEFAULT NULL COMMENT 'Exchange rate applied (orig → SEK)',
  `amount_sek` decimal(13,2) DEFAULT NULL COMMENT 'Amount converted to SEK',
  `vat_rate` decimal(5,2) DEFAULT NULL COMMENT 'Applicable VAT rate (%)',
  `vat_amount` decimal(13,2) DEFAULT NULL COMMENT 'VAT amount in SEK',
  `net_amount` decimal(13,2) DEFAULT NULL COMMENT 'Net amount excluding VAT',
  `gross_amount` decimal(13,2) DEFAULT NULL COMMENT 'Gross amount incl. VAT',
  `cost_center_override` varchar(100) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Optional cost center override',
  `project_code` varchar(100) COLLATE utf8mb4_swedish_ci DEFAULT NULL COMMENT 'Optional project code for accounting'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_swedish_ci COMMENT='Detail table with one row per purchase/transaction linked to main invoice';

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

--
-- Dumpning av Data i tabell `file_categories`
--

INSERT INTO `file_categories` (`id`, `name`, `description`, `created_at`) VALUES
(1, 'image', 'images', '2025-09-26 03:05:25'),
(2, 'audio', 'audio', '2025-09-26 03:05:25'),
(3, 'misc', 'misc\r\n', '2025-09-26 03:05:42'),
(4, 'video', 'video', '2025-09-26 03:05:42'),
(5, 'doc', 'documents, word, excel, pdf, md, txt', '2025-09-26 03:10:43');

-- --------------------------------------------------------

--
-- Tabellstruktur `file_locations`
--

CREATE TABLE `file_locations` (
  `id` bigint NOT NULL,
  `file_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'id from unified files',
  `lat` double DEFAULT NULL,
  `lon` double DEFAULT NULL,
  `acc` double DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `file_locations`
--

INSERT INTO `file_locations` (`id`, `file_id`, `lat`, `lon`, `acc`, `created_at`) VALUES
(1, '22890eab-2f5d-4bc7-b881-41a9da740e45', 59.41976478152312, 17.954069748680578, NULL, '2025-09-28 09:52:25'),
(2, '010fc9ec-2cb6-436e-b73c-a82ce7c4026a', 59.35087093052369, 17.96826839447022, NULL, '2025-09-28 09:52:26'),
(3, '998ac2c2-caa3-472d-9b04-f21785711961', 59.352693870029576, 17.96104917977293, NULL, '2025-09-28 09:52:27'),
(4, '361541f7-54de-4e45-bcc7-6a20d50135e6', 59.35269146104154, 17.961066321759077, NULL, '2025-09-28 09:52:28'),
(5, 'b447ba44-4162-4450-851e-0fd1ddd78d42', 59.353184472725225, 17.961222771488764, NULL, '2025-09-28 09:52:29'),
(6, '9d3150fb-1c4e-446a-8610-1281fd9e5c4b', 59.41979876795737, 17.954478064972214, NULL, '2025-09-28 09:52:30'),
(7, '744eab24-1d49-4705-a5d6-60aac05df151', 59.353466610545155, 17.961097404122828, NULL, '2025-09-28 09:52:31'),
(8, '9618aba4-6e2a-4c6a-8b6c-241aa825ca97', 59.3527166818701, 17.960909556687838, NULL, '2025-09-28 09:52:32'),
(9, '0ac43f53-6dd9-4e92-b3dd-538716b31108', 59.35269151661247, 17.96099525649056, NULL, '2025-09-28 09:52:33');

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
(1, 'jpg', 1, '2025-09-26 03:00:28'),
(2, 'jpeg', 1, '2025-09-26 03:00:28'),
(3, 'png', 1, '2025-09-26 03:08:14'),
(4, 'mp4', 4, '2025-09-26 03:08:14'),
(5, 'mkv', 4, '2025-09-26 03:08:14'),
(6, 'gif', 1, '2025-09-26 03:08:14'),
(7, 'webp', 1, '2025-09-26 03:08:30'),
(8, 'mp3', 2, '2025-09-26 03:08:30'),
(9, 'wav', 2, '2025-09-26 03:09:57'),
(10, 'doc', 5, '2025-09-26 03:09:57'),
(11, 'docx', 5, '2025-09-26 03:09:57'),
(12, 'pdf', 3, '2025-09-26 03:09:57'),
(13, 'xls', 5, '2025-09-26 03:12:03'),
(14, 'xlsx', 5, '2025-09-26 03:12:03');

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
('010fc9ec-2cb6-436e-b73c-a82ce7c4026a', '2', '2025-09-28 09:52:26'),
('0ac43f53-6dd9-4e92-b3dd-538716b31108', '2', '2025-09-28 09:52:33'),
('22890eab-2f5d-4bc7-b881-41a9da740e45', '9', '2025-09-28 09:52:25'),
('361541f7-54de-4e45-bcc7-6a20d50135e6', '2', '2025-09-28 09:52:28'),
('744eab24-1d49-4705-a5d6-60aac05df151', '2', '2025-09-28 09:52:31'),
('9618aba4-6e2a-4c6a-8b6c-241aa825ca97', '2', '2025-09-28 09:52:32'),
('998ac2c2-caa3-472d-9b04-f21785711961', '2', '2025-09-28 09:52:27'),
('9d3150fb-1c4e-446a-8610-1281fd9e5c4b', '2', '2025-09-28 09:52:30'),
('b447ba44-4162-4450-851e-0fd1ddd78d42', '2', '2025-09-28 09:52:29');

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
  `main_id` int NOT NULL COMMENT 'Referes to the unified_files.id',
  `article_id` varchar(222) NOT NULL COMMENT 'The unique product or article number that comes from the seller',
  `name` varchar(222) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'Product name',
  `number` int NOT NULL COMMENT 'The number of this item that was bought',
  `item_price_ex_vat` decimal(10,2) NOT NULL DEFAULT '0.00',
  `item_price_inc_vat` decimal(10,2) NOT NULL DEFAULT '0.00',
  `item_total_price_ex_vat` decimal(10,2) NOT NULL DEFAULT '0.00',
  `item_total_price_inc_vat` decimal(10,2) NOT NULL DEFAULT '0.00',
  `currency` varchar(11) NOT NULL DEFAULT 'SEK',
  `vat` decimal(10,2) NOT NULL DEFAULT '0.00',
  `vat_percentage` decimal(7,6) NOT NULL DEFAULT '0.000000'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Tabellstruktur `tags`
--

CREATE TABLE `tags` (
  `id` int NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `description` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `tag_category` int NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumpning av Data i tabell `tags`
--

INSERT INTO `tags` (`id`, `name`, `description`, `tag_category`, `created_at`) VALUES
(1, 'faktura', 'Uppladdade fakturor', 1, '2025-08-31 14:51:30'),
(2, 'kvitto', 'Uppladdade kvitton', 1, '2025-08-31 14:51:30'),
(3, 'selfie', 'Uppladdade selfies', 1, '2025-08-31 14:51:30'),
(4, 'transcript', 'Filer som ska transkriberas', 2, '2025-08-31 14:51:30'),
(5, 'mymusic', 'Egna låtar', 2, '2025-08-31 14:51:30'),
(6, 'samples', 'Egna samplingar', 2, '2025-08-31 14:51:30'),
(7, 'songs', 'Uppladdade bra låtar', 2, '2025-08-31 14:51:30'),
(8, 'docs', 'Uppladdade dokument', 3, '2025-08-31 14:51:30'),
(9, 'mixed', 'Övriga dokument', 3, '2025-08-31 14:51:30');

-- --------------------------------------------------------

--
-- Tabellstruktur `tag_categories`
--

CREATE TABLE `tag_categories` (
  `id` int NOT NULL,
  `tag_category_name` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `tag_category_description` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumpning av Data i tabell `tag_categories`
--

INSERT INTO `tag_categories` (`id`, `tag_category_name`, `tag_category_description`, `created_at`) VALUES
(1, 'photos', 'Photo files and images', '2025-08-31 14:51:30'),
(2, 'audio', 'Audio files and recordings', '2025-08-31 14:51:30'),
(3, 'misc', 'Miscellaneous files and documents', '2025-08-31 14:51:30');

-- --------------------------------------------------------

--
-- Tabellstruktur `unified_files`
--

CREATE TABLE `unified_files` (
  `id` varchar(36) NOT NULL,
  `file_type` varchar(32) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT NULL,
  `orgnr` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'Company Organization Number',
  `payment_type` varchar(255) NOT NULL COMMENT 'Enter "cash" or "card"',
  `purchase_datetime` datetime DEFAULT NULL COMMENT 'Date and time on the receipt',
  `expense_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'If this is bought using a private card or cash (personal) or if it is corporate card (corporate)',
  `gross_amount_original` decimal(12,2) DEFAULT NULL COMMENT 'amount inc vat',
  `net_amount_original` decimal(12,2) DEFAULT NULL COMMENT 'amount ex vat',
  `exchange_rate` decimal(12,0) NOT NULL COMMENT 'exchange rate example: 1 USD=11.33 SEK',
  `currency` varchar(222) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'SEK' COMMENT 'currency that was bought in',
  `gross_amount_sek` decimal(10,0) NOT NULL COMMENT 'only used for foreign currency - shows the gross amount in sek',
  `net_amount_sek` decimal(10,0) NOT NULL COMMENT 'The net amount in SEK after exchange conversion',
  `ai_status` varchar(32) DEFAULT NULL,
  `ai_confidence` float DEFAULT NULL,
  `mime_type` varchar(222) DEFAULT NULL,
  `ocr_raw` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'The raw ocr-text without coordinates from the picture',
  `company_id` int NOT NULL COMMENT 'companies.id - refering to the company that sold the product',
  `receipt_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'the unique receipt number',
  `file_creation_timestamp` timestamp NULL DEFAULT NULL COMMENT 'picked from the file when its fetched from ftp',
  `submitted_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT 'the logged in user that submitted the file',
  `original_file_id` varchar(36) DEFAULT NULL,
  `original_file_name` varchar(222) DEFAULT NULL,
  `original_file_size` int DEFAULT NULL,
  `file_suffix` varchar(32) DEFAULT NULL COMMENT 'File extension without dot',
  `file_category` int DEFAULT NULL COMMENT 'Reference to file_categories.id',
  `original_filename` varchar(255) DEFAULT NULL,
  `approved_by` int NOT NULL COMMENT 'user id that approved the receipt',
  `other_data` text NOT NULL COMMENT 'This is for all other data available on the receipt that doesnt have a specified column',
  `credit_card_match` tinyint(1) NOT NULL DEFAULT '0' COMMENT 'When matching receipt is available set 1'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `unified_files`
--

INSERT INTO `unified_files` (`id`, `file_type`, `created_at`, `updated_at`, `orgnr`, `payment_type`, `purchase_datetime`, `expense_type`, `gross_amount_original`, `net_amount_original`, `exchange_rate`, `currency`, `gross_amount_sek`, `net_amount_sek`, `ai_status`, `ai_confidence`, `mime_type`, `ocr_raw`, `company_id`, `receipt_number`, `file_creation_timestamp`, `submitted_by`, `original_file_id`, `original_file_name`, `original_file_size`, `file_suffix`, `file_category`, `original_filename`, `approved_by`, `other_data`, `credit_card_match`) VALUES
('010fc9ec-2cb6-436e-b73c-a82ce7c4026a', 'receipt', '2025-09-28 09:52:26', '2025-09-28 18:52:25', NULL, '', '2025-09-01 00:00:00', '', 123.45, NULL, 0, 'SEK', 0, 0, 'manual_review', 0.85, 'image/jpeg', 'EJ kvitto\nUBEREATS\n#76868\nHenleverans\nFramne:\n2025-09-01 16:00\nNann:\nMattias\n8 580 970 68\nTel:\n+46\nTel\n76 273\nkod:\n168\n1x\n220.0\nRigatoni\nCon Carne\n* Coca Cola Originil 33c1\n1x\nRigatoni\n220,0\nCon\nCarne\nCoca Cola\nZero 33ol\n1x\nRigatoni\nCon Carne\n220,0\n+ Coca-Cola\nZero 33cl\nTotal:\n660,0 kr\nPgearad oy aupile', 0, '', '2025-09-01 19:00:59', NULL, '4', 'photo_1756746059503_1.jpg', 1143142, 'jpg', 1, 'photo_68b5d14befd6b8.95349031.jpg', 0, '', 0),
('0ac43f53-6dd9-4e92-b3dd-538716b31108', 'receipt', '2025-09-28 09:52:33', '2025-09-28 18:52:16', NULL, '', '2025-09-07 00:00:00', '', 313.00, NULL, 0, 'SEK', 0, 0, 'manual_review', 0.85, 'image/jpeg', 'VERIFIERAD AV ENHET\nDEBIT\nPSN:00\nVisa\nVISA CONTACTLESS\n3632\nXXXX XXXX XXXX\n04709418-106957\nTERM\n30574008\nKF1\nATC:01765\nAED\nA0000000031010\nAID:\nSTATUS : 000\nARC:00\nAUKT.KOD:\n309300\nREF: 106957\nAUKTORISERAD\nResultat:\nBEHALL\nKVITTOT\nKUNDENS\nKVITTO\nBRUTTO\n1 25 %\n313,00\nMOMS\nNETTO\n62,60\n250,40\n55507732509070046816\nÖppet köp 9aller 1\ngaller obruten förPackning\n30\ndagar\nvaror\nSpara kvitto - galler\nbyte\n> Datum = leverans-\nSOM\n0773 2025-09-07 12:13 0004\noch\ngaranti\n0000\n<<', 0, '', '2025-09-25 12:48:12', NULL, '12', 'photo_1758797291061_1.jpg', 2863045, 'jpg', 1, 'photo_68d51dec3d2445.62262545.jpg', 0, '', 0),
('22890eab-2f5d-4bc7-b881-41a9da740e45', 'receipt', '2025-09-28 09:52:25', '2025-09-28 18:52:24', NULL, '', NULL, '', 123.45, NULL, 0, 'SEK', 0, 0, 'manual_review', 0.85, 'image/jpeg', 'aekcat\nVRPTEN\nENO\non', 0, '', '2025-08-31 21:22:09', NULL, '1', 'photo_1756668128632_1.jpg', 1169356, 'jpg', 1, 'photo_68b4a0e12436a2.02743784.jpg', 0, '', 0),
('361541f7-54de-4e45-bcc7-6a20d50135e6', 'receipt', '2025-09-28 09:52:28', '2025-09-28 18:52:17', NULL, '', '2025-09-05 00:00:00', '', 84.95, NULL, 0, 'SEK', 0, 0, 'manual_review', 0.85, 'image/jpeg', 'SKA\nUTGANG\nMS\nHandelsban SE\nBUTIKSNR: _30308472\nTERM: 40956875-1073220\n2025-09-05 18:32\nVisa DEBIT\nContactless\n************3632-0\nAID: A0000000031010\nTVR: 0000000000\nREF: 577633 180359 KF1\nRESP: 00\nPERIOD: 747\nKÖP\n5\nSEK\n84.95\nGODKÄNT\n6  6 80\nBAUHAUS\n16867 Bromma', 0, '', '2025-09-05 18:39:06', NULL, '6', 'photo_1757090345580_1.jpg', 1891504, 'jpg', 1, 'photo_68bb122a63d1b1.20796996.jpg', 0, '', 0),
('744eab24-1d49-4705-a5d6-60aac05df151', 'receipt', '2025-09-28 09:52:31', '2025-09-28 18:52:17', NULL, '', '2025-09-08 00:00:00', '', 358.90, NULL, 0, 'SEK', 0, 0, 'manual_review', 0.85, 'image/jpeg', 'SE\nMS\nHandelsban\n30308472\nBUTIKSNR:\nTERM:\n40956913-1073220\n2025-09-08 08:40\nVisa\nDEBIT\nContactless\n***********3632-0\nAID: A0000000031010\nTVR: 0000000000\nREF: 517982 135108 KF1\nRESP: 00\nPERIOD: 750\nKöP\n358.90\nSEK\nGODKÄNT\n8 3\n303\nBAUHAUS\n16867 Bromma\nSA', 0, '', '2025-09-08 08:42:33', NULL, '10', 'photo_1757313753128_1.jpg', 2142684, 'jpg', 1, 'photo_68be7ad9d1e7c3.81863965.jpg', 0, '', 0),
('9618aba4-6e2a-4c6a-8b6c-241aa825ca97', 'receipt', '2025-09-28 09:52:32', '2025-09-28 18:52:17', NULL, '', '2025-09-07 00:00:00', '', 313.00, NULL, 0, 'SEK', 0, 0, 'manual_review', 0.85, 'image/jpeg', 'HORNBACH\nDet\nfinns\nalltid\ngōra.\nnät\ntatt\nHornbach\nBy99marknad AB\nFilial\n773\nMadenvägen 17\n174 55 Sundbyber9\nTel. 08 - 799 50 00\nwww.hornbach.se\nMomsnr 556613-4853\n00\nART/EAN 7318140010944\n1 Styck\n×\n239,00\nTUNNA 75L\n239,00 1\nART/EAN 7318140010951\n1 Styck\n74,00\n×\nLOCK TILL TUNNA 75L\n74,00 1\nSumma [2]\nSEK\n313,00\nGIVET VISA\nSEK\n313,00\nHornbach Sundbyberg\nMadenvä9en 17\nSUNDBYBERG\nTel. Nr:\n087995000\nOrg.Nr:\n5566134853\n2025-09-07\n12:13\nKöP\nSEK 313.00\nVERIFIERAD AV ENHET\nVisa DEBIT\nPSN:00\nVISA CONTACTLESS\nXXXX XXXX XXXX 3632\nTERM:\n04709418-106957\n30574008\nKF1\nATC:01765\nAED:\nAID:\nA0000000031010\nARC:00\nSTATUS: 000\nAUKT.KOD:\n309300\nREF:106957\nResultat:\nAUKTORISERAD\nBEHALL KVITTOT\nKUNDENS KVITTO\nBRUTTO\nMOMS\nNETTO\n1 25 %\n313,00\n62,60\n250,40\n55507732509070046816\nÖppet köp 9äller 1 30 dagar,\ngäller obruten förpackning.\nBestälInings-/tillskurna varor,\nFiskar och växter ej öppet köp/eJ byte.\nSpara kvitto - galler som garanti.\n0773 2025-09-07 12:13 0004 000016 006816', 0, '', '2025-09-12 06:07:46', NULL, '11', 'photo_1757650065365_1.jpg', 1871790, 'jpg', 1, 'photo_68c39c92096163.69462592.jpg', 0, '', 0),
('998ac2c2-caa3-472d-9b04-f21785711961', 'receipt', '2025-09-28 09:52:27', '2025-09-28 18:52:19', NULL, '', '2025-09-01 00:00:00', '', 123.45, NULL, 0, 'SEK', 0, 0, 'manual_review', 0.85, 'image/jpeg', 'Ej\nkvitto\nUBEREATS\n#76868\nHemleverans\n16:00\n2025-09-01\nFramme:\nMattias\nNamn:\n8 586 970 68\n+46\nTel:\n76\n273\nkod:\n168\nTel\n1x\n220,0\nCon\nCarne\nRigatoni\nOriginal 33cl\nCoca-Cola\n1x\n220,0\nCon\nn Carne\nRigatoni\nCoca-Cola Zero 33cl\n1x\nCon Carne\n220,0\nRigatoni\nCoca-Cola Zero 33cl\n660,0 kr\nTotal:\nPauared by Qopla', 0, '', '2025-09-02 06:33:28', NULL, '5', 'photo_1756787608133_1.jpg', 2185897, 'jpg', 1, 'photo_68b6739890f7a7.62128365.jpg', 0, '', 0),
('9d3150fb-1c4e-446a-8610-1281fd9e5c4b', 'receipt', '2025-09-28 09:52:30', '2025-09-28 18:52:17', NULL, '', NULL, '', 123.45, NULL, 0, 'SEK', 0, 0, 'manual_review', 0.5, 'image/jpeg', '', 0, '', '2025-09-07 19:33:00', NULL, '9', 'photo_1757266379984_1.jpg', 1629839, 'jpg', 1, 'photo_68bdc1cc97f643.62743853.jpg', 0, '', 0),
('b447ba44-4162-4450-851e-0fd1ddd78d42', 'receipt', '2025-09-28 09:52:29', '2025-09-28 18:52:17', NULL, '', '2025-09-06 00:00:00', '', 261.80, NULL, 0, 'SEK', 0, 0, 'manual_review', 0.85, 'image/jpeg', '123\n122\n8\nOGOORA\n261.80\nSER\nAAX\n824\nPERIOD :\n00\nRRRES\nRAT\n5102696\n392192\nPERS\nTVR: 0000000000\nwd\nAID: A0000000031010\nd\n0-2************\nContactless\nDEBIT\nBSIA\n13:46\n2025-09-06\n40956913-1073220\nAMA\n30308472\nBUTIKSNR :\n-\nES\nHandeIsban\nSW\n1138\n52 60 90\n113\n8\n111\n12367\n: ^2\nBetJänad\n261,80\n52,36\n25%\nBrutto\nMWMS\nMoms%\n2000140729\nA\"nueae\n0o\n011000210\n:Juapund\n261,80\nPoo\n261,80\nDOTO\n-12.95\nAAA\n159.00\nRA\nLSR\nSNCA\n11.600\nBOÄSO\nA709\nOO\n5069-029696\nOON MOE\naammn\n2989\n2\nKarIsbodavägen\nBAUHAUS', 0, '', '2025-09-06 13:49:31', NULL, '7', 'photo_1757159367559_1.jpg', 2116861, 'jpg', 1, 'photo_68bc1fcb8fb2d1.19853966.jpg', 0, '', 0);

--
-- Index för dumpade tabeller
--

--
-- Index för tabell `ai_accounting_proposals`
--
ALTER TABLE `ai_accounting_proposals`
  ADD PRIMARY KEY (`id`);

--
-- Index för tabell `ai_llm`
--
ALTER TABLE `ai_llm`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `id` (`id`),
  ADD KEY `idx_ai_llm_enabled` (`enabled`);

--
-- Index för tabell `ai_llm_model`
--
ALTER TABLE `ai_llm_model`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `id` (`id`),
  ADD UNIQUE KEY `llm_id` (`llm_id`,`model_name`),
  ADD KEY `idx_ai_llm_model_llm_id` (`llm_id`),
  ADD KEY `idx_ai_llm_model_active` (`is_active`);

--
-- Index för tabell `ai_processing_history`
--
ALTER TABLE `ai_processing_history`
  ADD PRIMARY KEY (`id`);

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
  ADD UNIQUE KEY `id` (`id`),
  ADD UNIQUE KEY `prompt_key` (`prompt_key`);

--
-- Index för tabell `companies`
--
ALTER TABLE `companies`
  ADD PRIMARY KEY (`id`);

--
-- Index för tabell `creditcard_invoices_main`
--
ALTER TABLE `creditcard_invoices_main`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ux_invoice_number` (`invoice_number`),
  ADD KEY `ix_invoice_date` (`invoice_date`),
  ADD KEY `ix_invoice_number_long` (`invoice_number_long`);

--
-- Index för tabell `creditcard_invoice_items`
--
ALTER TABLE `creditcard_invoice_items`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ux_main_line` (`main_id`,`line_no`),
  ADD KEY `ix_main` (`main_id`),
  ADD KEY `ix_purchase_date` (`purchase_date`),
  ADD KEY `ix_merchant_name` (`merchant_name`);

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
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name_category` (`name`,`tag_category`),
  ADD KEY `tag_category` (`tag_category`);

--
-- Index för tabell `tag_categories`
--
ALTER TABLE `tag_categories`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `tag_category_name` (`tag_category_name`);

--
-- Index för tabell `unified_files`
--
ALTER TABLE `unified_files`
  ADD PRIMARY KEY (`id`);

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
  MODIFY `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT för tabell `ai_llm_model`
--
ALTER TABLE `ai_llm_model`
  MODIFY `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT för tabell `ai_processing_history`
--
ALTER TABLE `ai_processing_history`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=94;

--
-- AUTO_INCREMENT för tabell `ai_processing_queue`
--
ALTER TABLE `ai_processing_queue`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT för tabell `ai_system_prompts`
--
ALTER TABLE `ai_system_prompts`
  MODIFY `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT för tabell `companies`
--
ALTER TABLE `companies`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT för tabell `creditcard_invoices_main`
--
ALTER TABLE `creditcard_invoices_main`
  MODIFY `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Primary key, internal unique ID';

--
-- AUTO_INCREMENT för tabell `creditcard_invoice_items`
--
ALTER TABLE `creditcard_invoice_items`
  MODIFY `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Primary key, internal unique ID';

--
-- AUTO_INCREMENT för tabell `file_categories`
--
ALTER TABLE `file_categories`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

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
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT för tabell `tags`
--
ALTER TABLE `tags`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=388;

--
-- AUTO_INCREMENT för tabell `tag_categories`
--
ALTER TABLE `tag_categories`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- Restriktioner för dumpade tabeller
--

--
-- Restriktioner för tabell `creditcard_invoice_items`
--
ALTER TABLE `creditcard_invoice_items`
  ADD CONSTRAINT `fk_items_main` FOREIGN KEY (`main_id`) REFERENCES `creditcard_invoices_main` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

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

--
-- Restriktioner för tabell `tags`
--
ALTER TABLE `tags`
  ADD CONSTRAINT `tags_ibfk_1` FOREIGN KEY (`tag_category`) REFERENCES `tag_categories` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
