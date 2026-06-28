import { http } from '.'
import type { Template, TemplateSchema } from '@/types'

export function listTemplates(params?: { status?: string; keyword?: string }) {
  return http.get<any, Template[]>('/templates', { params })
}

export function createTemplate(payload: {
  name: string
  description?: string
  schema: TemplateSchema
}) {
  return http.post<any, Template>('/templates', payload)
}

export function getTemplate(id: number) {
  return http.get<any, Template>(`/templates/${id}`)
}

export function updateTemplate(id: number, payload: Partial<Template>) {
  return http.put<any, Template>(`/templates/${id}`, payload)
}

export function deleteTemplate(id: number) {
  return http.delete(`/templates/${id}`)
}

export function publishTemplate(id: number) {
  return http.post<any, Template>(`/templates/${id}/publish`)
}

export function archiveTemplate(id: number) {
  return http.post<any, Template>(`/templates/${id}/archive`)
}

export function batchDeleteTemplates(ids: number[]) {
  return http.post<any, { deleted: number }>('/templates/batch-delete', { ids })
}