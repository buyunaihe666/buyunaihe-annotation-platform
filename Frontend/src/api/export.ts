import { http } from '.'
import type { ExportRecord } from '@/types'

export function createExport(task_id: number, format: string) {
  return http.post<any, ExportRecord>('/export', { task_id, format })
}

export function listExports(task_id?: number) {
  return http.get<any, ExportRecord[]>('/export', {
    params: task_id ? { task_id } : undefined
  })
}

export function getExport(id: number) {
  return http.get<any, ExportRecord>(`/export/${id}`)
}