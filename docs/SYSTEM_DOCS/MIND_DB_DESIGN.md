-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Värd: mysql:3306
-- Tid vid skapande: 26 sep 2025 kl 03:14
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
  `account_code` varchar(32) NOT NULL,
  `debit` decimal(12,2) NOT NULL DEFAULT '0.00',
  `credit` decimal(12,2) NOT NULL DEFAULT '0.00',
  `vat_rate` decimal(6,2) DEFAULT NULL,
  `notes` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

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
(1, 'bf20dfeb-387f-4ec7-aeb8-34e9a59d44b1', 'ocr', 'error', '2025-09-22 03:45:58'),
(2, 'bf20dfeb-387f-4ec7-aeb8-34e9a59d44b1', 'classification', 'error', '2025-09-22 03:45:59'),
(3, '9bb87e0b-7626-4200-9a37-9ab3fa006f14', 'ocr', 'error', '2025-09-22 03:47:20'),
(4, '9bb87e0b-7626-4200-9a37-9ab3fa006f14', 'classification', 'error', '2025-09-22 03:47:20'),
(5, '2a29ca5e-157c-451c-a518-0a475163900a', 'ocr', 'error', '2025-09-22 03:49:00'),
(6, '2a29ca5e-157c-451c-a518-0a475163900a', 'classification', 'error', '2025-09-22 03:49:00'),
(7, '3b5b5b4d-b870-4545-ab32-f0dbd2f93ed2', 'ocr', 'error', '2025-09-22 03:50:26'),
(8, '3b5b5b4d-b870-4545-ab32-f0dbd2f93ed2', 'classification', 'error', '2025-09-22 03:50:26'),
(9, '9721b464-d2e0-4df4-a3df-b66b2652a3c3', 'ocr', 'success', '2025-09-25 07:52:53'),
(10, '74c25fd3-0660-4846-94fd-d0d462b98bce', 'ocr', 'success', '2025-09-25 07:52:53'),
(11, 'f2f2d179-c84b-498d-893b-bb75c52a4f4f', 'ocr', 'success', '2025-09-25 07:52:53'),
(12, '2b79026e-eaa8-426a-88ae-88e7ded457b9', 'ocr', 'success', '2025-09-25 07:52:53'),
(13, 'e6ac9602-2046-4f53-b76c-62f35b82815f', 'ocr', 'success', '2025-09-25 07:52:53'),
(14, 'f2f2d179-c84b-498d-893b-bb75c52a4f4f', 'classification', 'success', '2025-09-25 07:52:54'),
(15, '2b79026e-eaa8-426a-88ae-88e7ded457b9', 'classification', 'success', '2025-09-25 07:52:54'),
(16, 'e6ac9602-2046-4f53-b76c-62f35b82815f', 'classification', 'success', '2025-09-25 07:52:54'),
(17, '9721b464-d2e0-4df4-a3df-b66b2652a3c3', 'classification', 'success', '2025-09-25 07:52:54'),
(18, '74c25fd3-0660-4846-94fd-d0d462b98bce', 'classification', 'success', '2025-09-25 07:52:54'),
(19, 'f2f2d179-c84b-498d-893b-bb75c52a4f4f', 'validation', 'success', '2025-09-25 07:52:54'),
(20, '2b79026e-eaa8-426a-88ae-88e7ded457b9', 'validation', 'success', '2025-09-25 07:52:54'),
(21, 'e6ac9602-2046-4f53-b76c-62f35b82815f', 'validation', 'success', '2025-09-25 07:52:54'),
(22, '9721b464-d2e0-4df4-a3df-b66b2652a3c3', 'validation', 'success', '2025-09-25 07:52:54'),
(23, '74c25fd3-0660-4846-94fd-d0d462b98bce', 'validation', 'success', '2025-09-25 07:52:54'),
(24, 'b67c804d-2494-4e7b-9fff-038b53c1cf50', 'ocr', 'success', '2025-09-25 09:22:09'),
(25, '7e7fba6c-1786-44a6-a15a-1873add240cd', 'ocr', 'success', '2025-09-25 09:22:09'),
(26, 'e25cce77-09f1-44c0-bb70-35678a5f6ffe', 'ocr', 'success', '2025-09-25 09:22:09'),
(27, 'f3651f41-2e13-4c1e-82af-327a8ddefbbb', 'ocr', 'success', '2025-09-25 09:22:09'),
(28, '5530525e-4aea-4710-9827-7f5584cf6e56', 'ocr', 'success', '2025-09-25 09:22:09'),
(29, 'b67c804d-2494-4e7b-9fff-038b53c1cf50', 'classification', 'success', '2025-09-25 09:22:09'),
(30, '7e7fba6c-1786-44a6-a15a-1873add240cd', 'classification', 'success', '2025-09-25 09:22:09'),
(31, 'e25cce77-09f1-44c0-bb70-35678a5f6ffe', 'classification', 'success', '2025-09-25 09:22:09'),
(32, 'f3651f41-2e13-4c1e-82af-327a8ddefbbb', 'classification', 'success', '2025-09-25 09:22:09'),
(33, '5530525e-4aea-4710-9827-7f5584cf6e56', 'classification', 'success', '2025-09-25 09:22:09'),
(34, 'b67c804d-2494-4e7b-9fff-038b53c1cf50', 'validation', 'success', '2025-09-25 09:22:09'),
(35, '7e7fba6c-1786-44a6-a15a-1873add240cd', 'validation', 'success', '2025-09-25 09:22:09'),
(36, 'e25cce77-09f1-44c0-bb70-35678a5f6ffe', 'validation', 'success', '2025-09-25 09:22:09'),
(37, 'f3651f41-2e13-4c1e-82af-327a8ddefbbb', 'validation', 'success', '2025-09-25 09:22:09'),
(38, '5530525e-4aea-4710-9827-7f5584cf6e56', 'validation', 'success', '2025-09-25 09:22:09'),
(39, '2f47d8dd-0ffa-4659-9573-de2f5e56ec34', 'ocr', 'success', '2025-09-25 12:27:38'),
(40, 'd659a134-17d3-4834-b5fb-4ae01b9cce8b', 'ocr', 'success', '2025-09-25 12:27:38'),
(41, '2c6169e7-f734-4e40-a43f-36d076025f81', 'ocr', 'success', '2025-09-25 12:27:38'),
(42, 'b3e4b074-cc83-4634-87cf-4a1b97b3d3a0', 'ocr', 'success', '2025-09-25 12:27:38'),
(43, 'f4e83b8f-df0d-4d1b-af00-cab6680ee907', 'ocr', 'success', '2025-09-25 12:27:38'),
(44, '2f47d8dd-0ffa-4659-9573-de2f5e56ec34', 'classification', 'success', '2025-09-25 12:27:38'),
(45, 'd659a134-17d3-4834-b5fb-4ae01b9cce8b', 'classification', 'success', '2025-09-25 12:27:38'),
(46, '2c6169e7-f734-4e40-a43f-36d076025f81', 'classification', 'success', '2025-09-25 12:27:38'),
(47, 'b3e4b074-cc83-4634-87cf-4a1b97b3d3a0', 'classification', 'success', '2025-09-25 12:27:38'),
(48, 'f4e83b8f-df0d-4d1b-af00-cab6680ee907', 'classification', 'success', '2025-09-25 12:27:38'),
(49, '2f47d8dd-0ffa-4659-9573-de2f5e56ec34', 'validation', 'success', '2025-09-25 12:27:38'),
(50, 'd659a134-17d3-4834-b5fb-4ae01b9cce8b', 'validation', 'success', '2025-09-25 12:27:38'),
(51, '2c6169e7-f734-4e40-a43f-36d076025f81', 'validation', 'success', '2025-09-25 12:27:38'),
(52, 'b3e4b074-cc83-4634-87cf-4a1b97b3d3a0', 'validation', 'success', '2025-09-25 12:27:38'),
(53, 'f4e83b8f-df0d-4d1b-af00-cab6680ee907', 'validation', 'success', '2025-09-25 12:27:38'),
(54, '3d319f11-acdc-4389-9708-70f1ad836a70', 'ocr', 'success', '2025-09-25 12:52:34'),
(55, 'cbbefc73-5535-4aaf-8150-8a4a3cb752dd', 'ocr', 'success', '2025-09-25 12:52:34'),
(56, 'fa6b9b8b-0951-41f1-b320-0e7855e1d326', 'ocr', 'success', '2025-09-25 12:52:34'),
(57, '3a791e56-a241-4a2e-b541-549b883123fb', 'ocr', 'success', '2025-09-25 12:52:34'),
(58, '57f5dc51-2805-46f5-988e-a1d91a1e937b', 'ocr', 'success', '2025-09-25 12:52:34'),
(59, '3d319f11-acdc-4389-9708-70f1ad836a70', 'classification', 'success', '2025-09-25 12:52:34'),
(60, 'cbbefc73-5535-4aaf-8150-8a4a3cb752dd', 'classification', 'success', '2025-09-25 12:52:34'),
(61, 'fa6b9b8b-0951-41f1-b320-0e7855e1d326', 'classification', 'success', '2025-09-25 12:52:34'),
(62, '3a791e56-a241-4a2e-b541-549b883123fb', 'classification', 'success', '2025-09-25 12:52:34'),
(63, '57f5dc51-2805-46f5-988e-a1d91a1e937b', 'classification', 'success', '2025-09-25 12:52:34'),
(64, '3d319f11-acdc-4389-9708-70f1ad836a70', 'validation', 'success', '2025-09-25 12:52:34'),
(65, 'cbbefc73-5535-4aaf-8150-8a4a3cb752dd', 'validation', 'success', '2025-09-25 12:52:34'),
(66, 'fa6b9b8b-0951-41f1-b320-0e7855e1d326', 'validation', 'success', '2025-09-25 12:52:34'),
(67, '3a791e56-a241-4a2e-b541-549b883123fb', 'validation', 'success', '2025-09-25 12:52:34'),
(68, '57f5dc51-2805-46f5-988e-a1d91a1e937b', 'validation', 'success', '2025-09-25 12:52:34');

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
  `merchant_name` varchar(255) DEFAULT NULL,
  `orgnr` varchar(32) DEFAULT NULL,
  `purchase_datetime` datetime DEFAULT NULL,
  `gross_amount` decimal(12,2) DEFAULT NULL,
  `net_amount` decimal(12,2) DEFAULT NULL,
  `ai_status` varchar(32) DEFAULT NULL,
  `ai_confidence` float DEFAULT NULL,
  `submitted_by` varchar(64) DEFAULT NULL,
  `original_filename` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumpning av Data i tabell `unified_files`
--

INSERT INTO `unified_files` (`id`, `file_type`, `created_at`, `updated_at`, `merchant_name`, `orgnr`, `purchase_datetime`, `gross_amount`, `net_amount`, `ai_status`, `ai_confidence`, `submitted_by`, `original_filename`) VALUES
('05970616-b13d-4921-b424-d3d85d6316a6', 'receipt', '2025-09-25 16:32:26', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('14293b93-a9be-4d9e-bfc9-8da5344244c4', 'receipt', '2025-09-25 16:32:24', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('1862e282-1fc5-4130-920e-3dfa52a88654', 'receipt', '2025-09-25 16:32:23', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('1930c784-9e58-4f64-ac49-cb2df8c4d702', 'receipt', '2025-09-22 05:14:58', '2025-09-22 05:14:58', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('19db1d85-ba9e-4a9e-b105-953451700445', 'receipt', '2025-09-22 05:18:04', '2025-09-22 05:18:04', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('1e331563-e98f-42f8-96ea-de5b4d4e991b', 'receipt', '2025-09-25 16:32:25', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('1ecfc767-1c14-4f40-9533-ef23b13d2b7a', 'receipt', '2025-09-25 16:32:26', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('1f13fe75-4e2a-4837-afc0-b527fff274dc', 'receipt', '2025-09-22 05:18:03', '2025-09-22 05:18:03', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('25926195-6be1-4320-ac29-adac4c4c86ee', 'receipt', '2025-09-25 16:32:25', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('25f5a551-c141-4d47-ba68-4b4b35adcb40', 'receipt', '2025-09-22 05:14:57', '2025-09-22 05:14:57', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('2b79026e-eaa8-426a-88ae-88e7ded457b9', 'receipt', '2025-09-25 07:52:53', '2025-09-25 07:52:54', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('2c6169e7-f734-4e40-a43f-36d076025f81', 'receipt', '2025-09-25 12:27:38', '2025-09-25 12:27:38', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('2f47d8dd-0ffa-4659-9573-de2f5e56ec34', 'receipt', '2025-09-25 12:27:37', '2025-09-25 12:27:38', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('373a3b9e-0aa1-488b-9814-eb8bd67fd91c', 'receipt', '2025-09-22 05:18:03', '2025-09-22 05:18:04', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('3a791e56-a241-4a2e-b541-549b883123fb', 'receipt', '2025-09-25 12:52:33', '2025-09-25 12:52:34', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('3d319f11-acdc-4389-9708-70f1ad836a70', 'receipt', '2025-09-25 12:52:33', '2025-09-25 12:52:34', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('45c65e66-d1a3-4902-b1a2-f91424e3af53', 'receipt', '2025-09-22 05:18:02', '2025-09-22 05:18:02', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('48e6caf1-6a0d-4d9a-a316-8227799ad8a3', 'receipt', '2025-09-22 05:14:58', '2025-09-22 05:14:58', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('5530525e-4aea-4710-9827-7f5584cf6e56', 'receipt', '2025-09-25 09:22:09', '2025-09-25 09:22:09', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('57f5dc51-2805-46f5-988e-a1d91a1e937b', 'receipt', '2025-09-25 12:52:34', '2025-09-25 12:52:34', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('5c955f2e-a98b-416c-8c9f-3f6349c1c21c', 'receipt', '2025-09-22 05:18:02', '2025-09-22 05:18:02', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('5dd101b0-3335-43be-8c3b-2dc68f493ba5', 'receipt', '2025-09-22 05:14:59', '2025-09-22 05:14:59', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('6367bf2e-d3b1-4fb4-b3ed-ea98d05f5daf', 'receipt', '2025-09-22 05:14:58', '2025-09-22 05:14:58', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('6c122874-021b-4322-b27f-89d511f8e1cd', 'receipt', '2025-09-22 05:14:59', '2025-09-22 05:14:59', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('74c25fd3-0660-4846-94fd-d0d462b98bce', 'receipt', '2025-09-25 07:52:53', '2025-09-25 07:52:54', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('7a3e70b1-baf9-4e38-bf07-aa4706dcc475', 'receipt', '2025-09-22 05:18:02', '2025-09-22 05:18:02', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('7e7fba6c-1786-44a6-a15a-1873add240cd', 'receipt', '2025-09-25 09:22:09', '2025-09-25 09:22:09', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('824e7813-8711-4415-980c-210d53ef0d8b', 'receipt', '2025-09-25 16:32:25', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('8d6857f5-90e2-4639-8ee0-71bc05486b9f', 'receipt', '2025-09-25 16:32:24', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('8ef10706-78dd-4874-a909-a2be81df36b2', 'receipt', '2025-09-22 05:14:57', '2025-09-22 05:14:57', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('9721b464-d2e0-4df4-a3df-b66b2652a3c3', 'receipt', '2025-09-25 07:52:53', '2025-09-25 07:52:54', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('a7c951bb-0333-4f99-a17f-2696925a4d05', 'receipt', '2025-09-25 16:32:25', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('abf57153-ccb5-42cc-9a63-01a7662104d6', 'receipt', '2025-09-25 16:32:24', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('ac96207e-093b-464f-bb63-225239957d46', 'receipt', '2025-09-25 16:32:24', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('adb289c7-7505-4140-8475-c28660ad47d6', 'receipt', '2025-09-25 16:32:26', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('b3e4b074-cc83-4634-87cf-4a1b97b3d3a0', 'receipt', '2025-09-25 12:27:38', '2025-09-25 12:27:38', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('b67c804d-2494-4e7b-9fff-038b53c1cf50', 'receipt', '2025-09-25 09:22:09', '2025-09-25 09:22:09', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('c99aeed3-71dc-485e-9eec-c0a3e12e7d15', 'receipt', '2025-09-22 05:18:04', '2025-09-22 05:18:04', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('cbbefc73-5535-4aaf-8150-8a4a3cb752dd', 'receipt', '2025-09-25 12:52:33', '2025-09-25 12:52:34', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('d659a134-17d3-4834-b5fb-4ae01b9cce8b', 'receipt', '2025-09-25 12:27:37', '2025-09-25 12:27:38', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('d8d58dfc-ff8a-412f-96ed-f51234743e76', 'receipt', '2025-09-25 16:32:26', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('dac25fd1-faf7-4082-a84d-4c0638103d51', 'receipt', '2025-09-25 16:32:24', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('db44779f-b3f0-4e76-be3a-cac35eb62cb2', 'receipt', '2025-09-25 16:32:24', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('demo-0001', 'receipt', '2025-09-21 13:51:10', NULL, 'Demo Cafe', '556677-8899', '2025-09-21 13:51:10', 89.00, 71.20, 'new', 0.42, NULL, NULL),
('demo-0002', 'receipt', '2025-09-21 13:51:10', NULL, 'Grocer AB', '112233-4455', '2025-09-21 13:51:10', 245.50, 196.40, 'processed', 0.93, NULL, NULL),
('demo-0003', 'receipt', '2025-09-21 13:51:10', NULL, 'Tools & Co', '998877-6655', '2025-09-21 13:51:10', 1299.00, 1039.20, 'error', 0.12, NULL, NULL),
('demo-receipt-1', 'receipt', '2025-09-23 16:53:08', '2025-09-23 16:53:08', 'Demo Företag', '556677-8899', '2024-08-15 12:34:00', 250.75, 200.60, NULL, NULL, NULL, 'demo.jpg'),
('e25cce77-09f1-44c0-bb70-35678a5f6ffe', 'receipt', '2025-09-25 09:22:09', '2025-09-25 09:22:09', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('e3154b4e-6d83-4402-a6f7-5898518254f0', 'receipt', '2025-09-25 16:32:23', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('e6ac9602-2046-4f53-b76c-62f35b82815f', 'receipt', '2025-09-25 07:52:53', '2025-09-25 07:52:54', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('e92e1f35-1d26-4533-b3c8-3c930f0b0b07', 'receipt', '2025-09-22 05:18:03', '2025-09-22 05:18:03', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('eee22858-c9e5-479e-bb8a-2a8160ac317e', 'receipt', '2025-09-22 05:14:59', '2025-09-22 05:14:59', NULL, NULL, NULL, NULL, NULL, 'new', NULL, NULL, NULL),
('f0342134-b4b0-471c-92b8-b9c585cfa75c', 'receipt', '2025-09-25 16:32:23', '2025-09-25 16:32:27', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL),
('f2f2d179-c84b-498d-893b-bb75c52a4f4f', 'receipt', '2025-09-25 07:52:53', '2025-09-25 07:52:54', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('f3651f41-2e13-4c1e-82af-327a8ddefbbb', 'receipt', '2025-09-25 09:22:09', '2025-09-25 09:22:09', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('f4e83b8f-df0d-4d1b-af00-cab6680ee907', 'receipt', '2025-09-25 12:27:38', '2025-09-25 12:27:38', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('fa6b9b8b-0951-41f1-b320-0e7855e1d326', 'receipt', '2025-09-25 12:52:33', '2025-09-25 12:52:34', NULL, NULL, NULL, NULL, NULL, 'manual_review', 0.5, NULL, NULL),
('fa991c9f-6eae-419a-b14f-722d165576c9', 'receipt', '2025-09-25 16:32:23', '2025-09-25 16:32:26', NULL, NULL, NULL, NULL, NULL, 'queued', NULL, NULL, NULL);

--
-- Index för dumpade tabeller
--

--
-- Index för tabell `ai_accounting_proposals`
--
ALTER TABLE `ai_accounting_proposals`
  ADD PRIMARY KEY (`id`);

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
-- AUTO_INCREMENT för tabell `ai_processing_history`
--
ALTER TABLE `ai_processing_history`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=69;

--
-- AUTO_INCREMENT för tabell `ai_processing_queue`
--
ALTER TABLE `ai_processing_queue`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT för tabell `file_categories`
--
ALTER TABLE `file_categories`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT för tabell `file_locations`
--
ALTER TABLE `file_locations`
  MODIFY `id` bigint NOT NULL AUTO_INCREMENT;

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
