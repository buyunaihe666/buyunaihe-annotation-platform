import type { RoleCode, TaskStatus, TaskItemStatus, MaterialType } from '@/types'

export const ROLE_CODES: { code: RoleCode; label: string }[] = [
  { code: 'owner', label: '平台管理员' },
  { code: 'admin', label: '任务管理员' },
  { code: 'labeler', label: '标注员' },
  { code: 'reviewer', label: '审核员' },
  { code: 'agent', label: 'AI 智能体' }
]

export const ROLE_LABEL: Record<RoleCode, string> = {
  owner: '平台管理员',
  admin: '任务管理员',
  labeler: '标注员',
  reviewer: '审核员',
  agent: 'AI 智能体'
}

export const TASK_STATUS = {
  draft: { label: '草稿', type: 'info' as const },
  published: { label: '已发布', type: 'success' as const },
  paused: { label: '已暂停', type: 'warning' as const },
  completed: { label: '已完成', type: 'primary' as const },
  archived: { label: '已归档', type: 'info' as const }
}

export const TASK_ITEM_STATUS: Record<
  TaskItemStatus,
  { label: string; type: 'info' | 'success' | 'warning' | 'danger' | 'primary' }
> = {
  pending: { label: '待领取', type: 'info' },
  annotating: { label: '标注中', type: 'warning' },
  submitted: { label: '已提交', type: 'info' },
  ai_reviewing: { label: 'AI 审核中', type: 'warning' },
  reviewed: { label: '已审核', type: 'primary' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
  completed: { label: '已完成', type: 'success' }
}

export const MATERIAL_TYPES: { value: MaterialType; label: string; icon: string }[] = [
  { value: 'text', label: '单行文本', icon: 'EditPen' },
  { value: 'textarea', label: '多行文本', icon: 'Document' },
  { value: 'number', label: '数字', icon: 'Histogram' },
  { value: 'radio', label: '单选', icon: 'Select' },
  { value: 'checkbox', label: '多选', icon: 'Finished' },
  { value: 'select', label: '下拉选择', icon: 'ArrowDown' },
  { value: 'file', label: '文件', icon: 'Paperclip' },
  { value: 'image', label: '图片', icon: 'Picture' },
  { value: 'json', label: 'JSON', icon: 'Grid' },
  { value: 'llm_prompt', label: 'LLM 提示', icon: 'MagicStick' }
]

export const MATERIAL_TYPE_LABEL: Record<MaterialType, string> =
  MATERIAL_TYPES.reduce((acc, m) => {
    acc[m.value] = m.label
    return acc
  }, {} as Record<MaterialType, string>)

export const REVIEW_DECISIONS = [
  { value: 'approved', label: '通过', type: 'success' as const },
  { value: 'rejected', label: '驳回', type: 'danger' as const },
  { value: 'modify_approve', label: '修改后通过', type: 'warning' as const }
]

export const EXPORT_FORMATS = [
  { value: 'json', label: 'JSON' },
  { value: 'jsonl', label: 'JSONL' },
  { value: 'csv', label: 'CSV' },
  { value: 'xlsx', label: 'Excel (xlsx)' }
]