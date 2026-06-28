from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role_code: str
    avatar_url: Optional[str] = None
    status: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class UserCreate(BaseModel):
    username: str
    password: str
    nickname: Optional[str] = None
    role_code: str = "labeler"
    email: Optional[str] = None
    phone: Optional[str] = None


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    role_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[str] = None


class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None


class TemplateOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: str
    schema: Optional[Dict[str, Any]] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_orm_row(cls, row):
        return cls(
            id=row.id,
            name=row.name,
            description=row.description,
            status=row.status,
            schema=row.schema_json,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None


class DatasetOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    format: Optional[str] = None
    file_count: int
    item_count: int
    status: str
    field_mapping: Optional[Dict[str, Any]] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None


class MapFieldsRequest(BaseModel):
    mapping: Dict[str, str]


class DatasetItemOut(BaseModel):
    id: int
    dataset_id: int
    index: int
    raw_data: Optional[Dict[str, Any]] = None
    mapped_fields: Optional[Dict[str, Any]] = None
    status: str


class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
    template_id: Optional[int] = None
    dataset_id: Optional[int] = None
    enable_ai_audit: bool = True
    enable_ai_suggestion: bool = True
    # 资源配置
    quota: int = 0
    deadline: Optional[datetime] = None
    reward_rules: Optional[Dict[str, Any]] = None
    # 分类与分发配置
    tags: Optional[List[str]] = None
    distribution_type: str = "first_come_first_serve"
    # AI 预审配置
    ai_audit_config: Optional[Dict[str, Any]] = None


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_id: Optional[int] = None
    dataset_id: Optional[int] = None
    enable_ai_audit: Optional[bool] = None
    enable_ai_suggestion: Optional[bool] = None
    quota: Optional[int] = None
    deadline: Optional[datetime] = None
    reward_rules: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    distribution_type: Optional[str] = None
    ai_audit_config: Optional[Dict[str, Any]] = None


class TaskOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    template_id: Optional[int] = None
    dataset_id: Optional[int] = None
    status: str
    enable_ai_audit: int
    enable_ai_suggestion: int
    quota: int = 0
    max_item_count: int = 0
    deadline: Optional[datetime] = None
    reward_rules: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    distribution_type: str = "first_come_first_serve"
    ai_audit_config: Optional[Dict[str, Any]] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None


class AssignmentIn(BaseModel):
    user_id: int
    role: str
    review_order: int = 0  # 审核链路顺序


class AssignRequest(BaseModel):
    assignments: List[AssignmentIn]


class TaskItemOut(BaseModel):
    id: int
    task_id: int
    dataset_item_id: Optional[int]
    index: int
    status: str
    assigned_labeler_id: Optional[int] = None
    assigned_reviewer_id: Optional[int] = None


class TaskItemDetail(BaseModel):
    item: TaskItemOut
    template_schema: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    suggestion: Optional[Dict[str, Any]] = None


class DraftRequest(BaseModel):
    result: Dict[str, Any]


class DecisionRequest(BaseModel):
    decision: str
    comment: Optional[str] = None


class ExportRequest(BaseModel):
    task_id: int
    format: str
    fields: Optional[List[str]] = None  # 选择导出哪些字段


class ExportRecordOut(BaseModel):
    id: int
    task_id: int
    format: str
    status: str
    total: int
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    files: Optional[List[Dict[str, Any]]] = None