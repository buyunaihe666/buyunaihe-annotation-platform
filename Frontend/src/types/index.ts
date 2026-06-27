export type RoleCode = 'owner' | 'admin' | 'labeler' | 'reviewer' | 'agent'

export interface User {
  id: number
  username: string
  nickname?: string
  email?: string
  phone?: string
  role_code: RoleCode
  avatar_url?: string
  status?: string
  created_at?: string
}

export interface LoginResult {
  token: string
  user: User
}

export type MaterialType =
  | 'text'
  | 'textarea'
  | 'number'
  | 'radio'
  | 'checkbox'
  | 'select'
  | 'file'
  | 'image'
  | 'json'
  | 'llm_prompt'

export interface Material {
  id: string
  fieldKey: string
  label: string
  type: MaterialType
  required?: boolean
  options?: string[]
  props?: Record<string, any>
  sortOrder?: number
}

export interface TemplateSchema {
  materials: Material[]
}

export type TemplateStatus = 'draft' | 'published' | 'archived'

export interface Template {
  id: number
  name: string
  description?: string
  status: TemplateStatus
  schema: TemplateSchema
  created_by?: number
  created_at?: string
  updated_at?: string
}

export interface Dataset {
  id: number
  name: string
  description?: string
  format?: string
  file_count?: number
  item_count?: number
  status?: string
  field_mapping?: Record<string, string>
  created_by?: number
  created_at?: string
  updated_at?: string
}

export interface DatasetItem {
  id: number
  dataset_id: number
  index: number
  raw_data: Record<string, any>
  mapped_fields?: Record<string, any>
  status?: string
}

export interface DatasetItemsPage {
  items: DatasetItem[]
  total: number
  fields: string[]
}

export type TaskStatus =
  | 'draft'
  | 'published'
  | 'paused'
  | 'completed'
  | 'archived'

export interface Task {
  id: number
  name: string
  description?: string
  template_id?: number
  dataset_id?: number
  status: TaskStatus
  enable_ai_audit: number | boolean
  enable_ai_suggestion: number | boolean
  template?: Template
  dataset?: Dataset
  progress?: TaskProgress
  created_by?: number
  created_at?: string
  updated_at?: string
}

export type TaskItemStatus =
  | 'pending'
  | 'annotating'
  | 'submitted'
  | 'ai_reviewing'
  | 'reviewed'
  | 'approved'
  | 'rejected'
  | 'completed'

export interface TaskItem {
  id: number
  task_id: number
  dataset_item_id?: number
  index: number
  status: TaskItemStatus
  assigned_labeler_id?: number
  assigned_reviewer_id?: number
  created_at?: string
  updated_at?: string
}

export interface TaskProgress {
  task_id?: number
  total: number
  pending: number
  annotating: number
  submitted: number
  ai_reviewing: number
  reviewed: number
  approved: number
  rejected: number
  completed: number
}

export interface TaskAssignment {
  id: number
  task_id: number
  user_id: number
  role: string
  assigned_at: string
  user?: User
}

export interface AnnotationItemResponse {
  item: TaskItem
  template_schema: TemplateSchema
  raw_data: Record<string, any>
  result: Record<string, any> | null
  suggestion?: any
}

export interface SuggestionState {
  suggestion_id: string
  status: 'pending' | 'generating' | 'done' | 'error'
  suggestion?: any
}

export interface ReviewItemResponse {
  item: TaskItem
  template_schema: TemplateSchema
  raw_data: Record<string, any>
  result: Record<string, any> | null
  ai_report?: AiReport
}

export interface AiReport {
  audit_id?: string
  status: 'processing' | 'done' | 'error' | 'pending'
  score?: number
  issues?: string[]
  reasoning?: string
  suggestion?: string
  evidence?: any
  model?: string
  error?: string
}

export type ReviewDecision = 'approved' | 'rejected' | 'modify_approve'

export interface ExportRecord {
  id: number
  task_id: number
  format: string
  status: string
  total: number
  created_by?: number
  created_at?: string
  completed_at?: string
  files?: ExportFile[]
}

export interface ExportFile {
  id: number
  minio_object: string
  filename: string
  size: number
  url?: string
}

export interface StatsOverview {
  task_count: number
  dataset_count: number
  template_count: number
  user_count: number
  pending_review: number
  completed_items: number
}

export interface StatsTimelinePoint {
  date: string
  completed: number
}

export interface LabelerStat {
  user_id: number
  username: string
  nickname?: string
  annotated: number
  approved: number
  rejected: number
}

export interface TaskStatsResponse {
  progress: TaskProgress
  labeler_stats: LabelerStat[]
  timeline: StatsTimelinePoint[]
}

export interface ApiEnvelope<T = any> {
  code: number
  message: string
  data: T
}