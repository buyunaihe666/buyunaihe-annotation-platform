from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    String,
    JSON,
   DECIMAL,
 func,
)
from sqlalchemy.orm import relationship

from .database import Base

# Cross-database primary key type: BigInteger on PostgreSQL/MySQL,
# Integer on SQLite (SQLite only auto-increments INTEGER PRIMARY KEY).
PK = BigInteger().with_variant(Integer, "sqlite")


class Role(Base):
    __tablename__ = "roles"
    id = Column(PK, primary_key=True, autoincrement=True)
    code = Column(String(32), nullable=False, unique=True)
    name = Column(String(64), nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime, server_default=func.current_timestamp())


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(PK, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, unique=True)
    name = Column(String(128), nullable=False)
    module = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(PK, primary_key=True)
    permission_id = Column(PK, primary_key=True)


class User(Base):
    __tablename__ = "users"
    id = Column(PK, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(64))
    email = Column(String(128))
    phone = Column(String(32))
    role_code = Column(String(32), nullable=False, default="labeler")
    avatar_url = Column(String(512))
    status = Column(String(16), nullable=False, default="active")
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class Template(Base):
    __tablename__ = "templates"
    id = Column(PK, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(String(512))
    status = Column(String(16), nullable=False, default="draft")
    schema_json = Column(JSON)
    created_by = Column(BigInteger)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(PK, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(String(512))
    format = Column(String(16))
    file_count = Column(Integer, nullable=False, default=0)
    item_count = Column(Integer, nullable=False, default=0)
    status = Column(String(16), nullable=False, default="active")
    field_mapping_json = Column(JSON)
    created_by = Column(BigInteger)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class DatasetFile(Base):
    __tablename__ = "dataset_files"
    id = Column(PK, primary_key=True, autoincrement=True)
    dataset_id = Column(BigInteger, nullable=False)
    filename = Column(String(255), nullable=False)
    minio_object = Column(String(512), nullable=False)
    size = Column(BigInteger, nullable=False, default=0)
    format = Column(String(16))
    status = Column(String(16), nullable=False, default="uploaded")
    created_at = Column(DateTime, server_default=func.current_timestamp())


class DatasetItem(Base):
    __tablename__ = "dataset_items"
    id = Column(PK, primary_key=True, autoincrement=True)
    dataset_id = Column(BigInteger, nullable=False)
    file_id = Column(BigInteger)
    index = Column(Integer, nullable=False, default=0)
    raw_data = Column(JSON)
    mapped_fields = Column(JSON)
    status = Column(String(16), nullable=False, default="pending")
    created_at = Column(DateTime, server_default=func.current_timestamp())


class Task(Base):
    __tablename__ = "tasks"
    id = Column(PK, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(String(512))
    template_id = Column(BigInteger)
    dataset_id = Column(BigInteger)
    status = Column(String(24), nullable=False, default="draft")
    enable_ai_audit = Column(Integer, nullable=False, default=1)
    enable_ai_suggestion = Column(Integer, nullable=False, default=1)

    # --- 资源配置 ---
    quota = Column(Integer, nullable=False, default=0)  # 任务配额（最大不能超过数据集总量）
    max_item_count = Column(Integer, nullable=False, default=0)  # 数据集总量
    deadline = Column(DateTime)  # 截止时间
    reward_rules = Column(JSON)  # 奖励规则 {"per_item": 0.5, "bonus_approved": 1.0}

    # --- 分类与分发配置 ---
    tags = Column(JSON)  # 标签列表 ["文本","情感"]
    distribution_type = Column(String(24), nullable=False, default="first_come_first_serve")  # first_come_first_serve | assigned

    # --- AI 预审配置 ---
    ai_audit_config = Column(JSON)  # {"audit_prompt": "...", "pass_score": 80, "review_score": 60, "dimensions": [{"name":"准确性","weight":0.5},{"name":"完整性","weight":0.3},{"name":"一致性","weight":0.2}]}

    created_by = Column(BigInteger)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    id = Column(PK, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    role = Column(String(16), nullable=False)
    review_order = Column(Integer, default=0)  # 审核链路顺序（0=非审核员, 1+=审核链路位置）
    assigned_at = Column(DateTime, server_default=func.current_timestamp())


class TaskItem(Base):
    __tablename__ = "task_items"
    id = Column(PK, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, nullable=False)
    dataset_item_id = Column(BigInteger)
    index = Column(Integer, nullable=False, default=0)
    status = Column(String(24), nullable=False, default="pending")
    assigned_labeler_id = Column(BigInteger)
    assigned_reviewer_id = Column(BigInteger)
    current_reviewer_id = Column(BigInteger)  # 当前在审核链中的审核员
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class TaskTransition(Base):
    __tablename__ = "task_transitions"
    id = Column(PK, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, nullable=False)
    task_item_id = Column(BigInteger, nullable=False)
    from_status = Column(String(24))
    to_status = Column(String(24), nullable=False)
    operator_id = Column(BigInteger)
    operator_type = Column(String(16), nullable=False, default="user")
    comment = Column(String(512))
    created_at = Column(DateTime, server_default=func.current_timestamp())


class TaskProgress(Base):
    __tablename__ = "task_progress"
    task_id = Column(PK, primary_key=True)
    total = Column(Integer, nullable=False, default=0)
    pending = Column(Integer, nullable=False, default=0)
    annotating = Column(Integer, nullable=False, default=0)
    submitted = Column(Integer, nullable=False, default=0)
    ai_reviewing = Column(Integer, nullable=False, default=0)
    reviewed = Column(Integer, nullable=False, default=0)
    approved = Column(Integer, nullable=False, default=0)
    rejected = Column(Integer, nullable=False, default=0)
    completed = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class AnnotationResult(Base):
    __tablename__ = "annotation_results"
    id = Column(PK, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, nullable=False)
    task_item_id = Column(BigInteger, nullable=False, unique=True)
    labeler_id = Column(BigInteger, nullable=False)
    result = Column(JSON)
    ai_suggestion_id = Column(String(64))
    ai_report_id = Column(String(64))
    status = Column(String(16), nullable=False, default="draft")
    submitted_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class ReviewOpinion(Base):
    __tablename__ = "review_opinions"
    id = Column(PK, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, nullable=False)
    task_item_id = Column(BigInteger, nullable=False)
    reviewer_id = Column(BigInteger, nullable=False)
    decision = Column(String(16), nullable=False)
    comment = Column(String(512))
    ai_report_id = Column(String(64))
    created_at = Column(DateTime, server_default=func.current_timestamp())


class ExportRecord(Base):
    __tablename__ = "export_records"
    id = Column(PK, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, nullable=False)
    format = Column(String(16), nullable=False)
    status = Column(String(16), nullable=False, default="pending")
    total = Column(Integer, nullable=False, default=0)
    created_by = Column(BigInteger)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    completed_at = Column(DateTime)


class ExportFile(Base):
    __tablename__ = "export_files"
    id = Column(PK, primary_key=True, autoincrement=True)
    export_record_id = Column(BigInteger, nullable=False)
    minio_object = Column(String(512), nullable=False)
    filename = Column(String(255), nullable=False)
    size = Column(BigInteger, nullable=False, default=0)
    url = Column(String(512))
    created_at = Column(DateTime, server_default=func.current_timestamp())