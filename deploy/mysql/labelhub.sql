-- Buyunaihe main business database (PostgreSQL)
-- Tables are created automatically by the backend on startup via SQLAlchemy
-- Base.metadata.create_all(). This script only seeds reference data.

-- Seed roles (idempotent)
INSERT INTO roles (code, name, description) VALUES
  ('owner', 'Owner / 管理员', '平台管理员，拥有全部权限'),
  ('admin', 'Admin / 管理员', '任务管理员'),
  ('labeler', 'Labeler / 标注员', '领取任务并完成标注'),
  ('reviewer', 'Reviewer / 审核员', '审核标注结果'),
  ('agent', 'AI Agent', 'AI 智能体角色')
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name;

-- Default users are seeded by the backend on first startup.
