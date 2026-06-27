-- Buyunaihe AI Agent results database (isolated from main business DB)
CREATE DATABASE IF NOT EXISTS `labelhub_agent` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Grant the application user (created by the MySQL container from MYSQL_USER/MYSQL_PASSWORD)
-- full privileges on the agent database. The container only auto-grants MYSQL_DATABASE.
GRANT ALL PRIVILEGES ON `labelhub_agent`.* TO 'labelhub'@'%';
FLUSH PRIVILEGES;

USE `labelhub_agent`;

CREATE TABLE IF NOT EXISTS `ai_suggestions` (
  `id` VARCHAR(64) NOT NULL,
  `task_id` BIGINT NOT NULL,
  `task_item_id` BIGINT NOT NULL,
  `labeler_id` BIGINT NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'pending',
  `suggestion` JSON NULL,
  `model` VARCHAR(64) NULL,
  `error` VARCHAR(512) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` DATETIME NULL,
  PRIMARY KEY (`id`),
  KEY `idx_sug_item` (`task_item_id`),
  KEY `idx_sug_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `ai_audit_reports` (
  `id` VARCHAR(64) NOT NULL,
  `task_id` BIGINT NOT NULL,
  `task_item_id` BIGINT NOT NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'pending',
  `score` DECIMAL(5,2) NULL,
  `issues` JSON NULL,
  `reasoning` TEXT NULL,
  `suggestion` TEXT NULL,
  `evidence` JSON NULL,
  `model` VARCHAR(64) NULL,
  `error` VARCHAR(512) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` DATETIME NULL,
  PRIMARY KEY (`id`),
  KEY `idx_audit_item` (`task_item_id`),
  KEY `idx_audit_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
