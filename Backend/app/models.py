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


class Role(Base):
    __tablename__ = "roles"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(32), nullable=False, unique=True)
    name = Column(String(64), nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime, server_default=func.current_timestamp())


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, unique=True)
    name = Column(String(128), nullable=False)
    module = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.current_timestamp())


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(BigInteger, primary_key=True)
    permission_id = Column(BigInteger, primary_key=True)


class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
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
    id = Column(BigInteger, primary_key=True, autoincrement=True)
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
    id = Column(BigInteger, primary_key=True, autoincrement=True)
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
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id = Column(BigInteger, nullable=False)
    filename = Column(String(255), nullable=False)
    minio_object = Column(String(512), nullable=False)
    size = Column(BigInteger, nullable=False, default=0)
    format = Column(String(16))
    status = Column(String(16), nullable=False, default="uploaded")
    created_at = Column(DateTime, server_default=func.current_timestamp())


class DatasetItem(Base):
    __tablename__ = "dataset_items"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    dataset_id = Column(BigInteger, nullable=False)
    file_id = Column(BigInteger)
    index = Column(Integer, nullable=False, default=0)
    raw_data = Column(JSON)
    mapped_fields = Column(JSON)
    status = Column(String(16), nullable=False, default="pending")
    created_at = Column(DateTime, server_default=func.current_timestamp())


class Task(Base):
    __tablename__ = "tasks"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(String(512))
    template_id = Column(BigInteger)
    dataset_id = Column(BigInteger)
    status = Column(String(24), nullable=False, default="draft")
    enable_ai_audit = Column(Integer, nullable=False, default=1)
    enable_ai_suggestion = Column(Integer, nullable=False, default=1)
    created_by = Column(BigInteger)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    role = Column(String(16), nullable=False)
    assigned_at = Column(DateTime, server_default=func.current_timestamp())


class TaskItem(Base):
    __tablename__ = "task_items"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, nullable=False)
    dataset_item_id = Column(BigInteger)
    index = Column(Integer, nullable=False, default=0)
    status = Column(String(24), nullable=False, default="pending")
    assigned_labeler_id = Column(BigInteger)
    assigned_reviewer_id = Column(BigInteger)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class TaskTransition(Base):
    __tablename__ = "task_transitions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
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
    task_id = Column(BigInteger, primary_key=True)
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
    id = Column(BigInteger, primary_key=True, autoincrement=True)
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
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, nullable=False)
    task_item_id = Column(BigInteger, nullable=False)
    reviewer_id = Column(BigInteger, nullable=False)
    decision = Column(String(16), nullable=False)
    comment = Column(String(512))
    ai_report_id = Column(String(64))
    created_at = Column(DateTime, server_default=func.current_timestamp())


class ExportRecord(Base):
    __tablename__ = "export_records"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, nullable=False)
    format = Column(String(16), nullable=False)
    status = Column(String(16), nullable=False, default="pending")
    total = Column(Integer, nullable=False, default=0)
    created_by = Column(BigInteger)
    created_at = Column(DateTime, server_default=func.current_timestamp())
    completed_at = Column(DateTime)


class ExportFile(Base):
    __tablename__ = "export_files"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    export_record_id = Column(BigInteger, nullable=False)
    minio_object = Column(String(512), nullable=False)
    filename = Column(String(255), nullable=False)
    size = Column(BigInteger, nullable=False, default=0)
    url = Column(String(512))
    created_at = Column(DateTime, server_default=func.current_timestamp())