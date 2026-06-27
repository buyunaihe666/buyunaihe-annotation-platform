-- Buyunaihe main business database
CREATE DATABASE IF NOT EXISTS `labelhub` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `labelhub`;

-- ===== User & permission domain =====
CREATE TABLE IF NOT EXISTS `roles` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(32) NOT NULL,
  `name` VARCHAR(64) NOT NULL,
  `description` VARCHAR(255) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `permissions` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `code` VARCHAR(64) NOT NULL,
  `name` VARCHAR(128) NOT NULL,
  `module` VARCHAR(64) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_perm_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `role_permissions` (
  `role_id` BIGINT NOT NULL,
  `permission_id` BIGINT NOT NULL,
  PRIMARY KEY (`role_id`, `permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `users` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(64) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `nickname` VARCHAR(64) NULL,
  `email` VARCHAR(128) NULL,
  `phone` VARCHAR(32) NULL,
  `role_code` VARCHAR(32) NOT NULL DEFAULT 'labeler',
  `avatar_url` VARCHAR(512) NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'active',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===== Template config domain =====
CREATE TABLE IF NOT EXISTS `templates` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(128) NOT NULL,
  `description` VARCHAR(512) NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'draft',
  `schema_json` JSON NULL,
  `created_by` BIGINT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_template_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===== Dataset domain =====
CREATE TABLE IF NOT EXISTS `datasets` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(128) NOT NULL,
  `description` VARCHAR(512) NULL,
  `format` VARCHAR(16) NULL,
  `file_count` INT NOT NULL DEFAULT 0,
  `item_count` INT NOT NULL DEFAULT 0,
  `status` VARCHAR(16) NOT NULL DEFAULT 'active',
  `field_mapping_json` JSON NULL,
  `created_by` BIGINT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `dataset_files` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `dataset_id` BIGINT NOT NULL,
  `filename` VARCHAR(255) NOT NULL,
  `minio_object` VARCHAR(512) NOT NULL,
  `size` BIGINT NOT NULL DEFAULT 0,
  `format` VARCHAR(16) NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'uploaded',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_dataset_files_ds` (`dataset_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `dataset_items` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `dataset_id` BIGINT NOT NULL,
  `file_id` BIGINT NULL,
  `index` INT NOT NULL DEFAULT 0,
  `raw_data` JSON NULL,
  `mapped_fields` JSON NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'pending',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_dataset_items_ds` (`dataset_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===== Task processing domain =====
CREATE TABLE IF NOT EXISTS `tasks` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(128) NOT NULL,
  `description` VARCHAR(512) NULL,
  `template_id` BIGINT NULL,
  `dataset_id` BIGINT NULL,
  `status` VARCHAR(24) NOT NULL DEFAULT 'draft',
  `enable_ai_audit` TINYINT NOT NULL DEFAULT 1,
  `enable_ai_suggestion` TINYINT NOT NULL DEFAULT 1,
  `created_by` BIGINT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_task_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `task_assignments` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `task_id` BIGINT NOT NULL,
  `user_id` BIGINT NOT NULL,
  `role` VARCHAR(16) NOT NULL,
  `assigned_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_user_role` (`task_id`, `user_id`, `role`),
  KEY `idx_assign_task` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `task_items` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `task_id` BIGINT NOT NULL,
  `dataset_item_id` BIGINT NULL,
  `index` INT NOT NULL DEFAULT 0,
  `status` VARCHAR(24) NOT NULL DEFAULT 'pending',
  `assigned_labeler_id` BIGINT NULL,
  `assigned_reviewer_id` BIGINT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_taskitem_task` (`task_id`),
  KEY `idx_taskitem_labeler` (`assigned_labeler_id`, `status`),
  KEY `idx_taskitem_reviewer` (`assigned_reviewer_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `task_transitions` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `task_id` BIGINT NOT NULL,
  `task_item_id` BIGINT NOT NULL,
  `from_status` VARCHAR(24) NULL,
  `to_status` VARCHAR(24) NOT NULL,
  `operator_id` BIGINT NULL,
  `operator_type` VARCHAR(16) NOT NULL DEFAULT 'user',
  `comment` VARCHAR(512) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_trans_item` (`task_item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `task_progress` (
  `task_id` BIGINT NOT NULL,
  `total` INT NOT NULL DEFAULT 0,
  `pending` INT NOT NULL DEFAULT 0,
  `annotating` INT NOT NULL DEFAULT 0,
  `submitted` INT NOT NULL DEFAULT 0,
  `ai_reviewing` INT NOT NULL DEFAULT 0,
  `reviewed` INT NOT NULL DEFAULT 0,
  `approved` INT NOT NULL DEFAULT 0,
  `rejected` INT NOT NULL DEFAULT 0,
  `completed` INT NOT NULL DEFAULT 0,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===== Annotation & review domain =====
CREATE TABLE IF NOT EXISTS `annotation_results` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `task_id` BIGINT NOT NULL,
  `task_item_id` BIGINT NOT NULL,
  `labeler_id` BIGINT NOT NULL,
  `result` JSON NULL,
  `ai_suggestion_id` VARCHAR(64) NULL,
  `ai_report_id` VARCHAR(64) NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'draft',
  `submitted_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_result_item` (`task_item_id`),
  KEY `idx_result_task` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `review_opinions` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `task_id` BIGINT NOT NULL,
  `task_item_id` BIGINT NOT NULL,
  `reviewer_id` BIGINT NOT NULL,
  `decision` VARCHAR(16) NOT NULL,
  `comment` VARCHAR(512) NULL,
  `ai_report_id` VARCHAR(64) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_review_item` (`task_item_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===== Export domain =====
CREATE TABLE IF NOT EXISTS `export_records` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `task_id` BIGINT NOT NULL,
  `format` VARCHAR(16) NOT NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'pending',
  `total` INT NOT NULL DEFAULT 0,
  `created_by` BIGINT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` DATETIME NULL,
  PRIMARY KEY (`id`),
  KEY `idx_export_task` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `export_files` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `export_record_id` BIGINT NOT NULL,
  `minio_object` VARCHAR(512) NOT NULL,
  `filename` VARCHAR(255) NOT NULL,
  `size` BIGINT NOT NULL DEFAULT 0,
  `url` VARCHAR(512) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_exportfile_rec` (`export_record_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===== Seed data =====
INSERT INTO `roles` (`code`, `name`, `description`) VALUES
  ('owner', 'Owner / 管理员', '平台管理员，拥有全部权限'),
  ('admin', 'Admin / 管理员', '任务管理员'),
  ('labeler', 'Labeler / 标注员', '领取任务并完成标注'),
  ('reviewer', 'Reviewer / 审核员', '审核标注结果'),
  ('agent', 'AI Agent', 'AI 智能体角色')
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`);

-- Default users are seeded by the backend on first startup (with a correct bcrypt
-- hash of "123456"). Do NOT insert users here with a placeholder hash — the backend
-- only creates users that are missing and will not overwrite an existing hash.
