import { http } from '.'
import type { ExportRecord } from '@/types'

export function createExport(task_id: number, format: string, fields?: string[]) {
  return http.post<any, ExportRecord>('/export', { task_id, format, fields })
}

export function listExports(task_id?: number) {
  return http.get<any, ExportRecord[]>('/export', {
    params: task_id ? { task_id } : undefined
  })
}

export function getExport(id: number) {
  return http.get<any, ExportRecord>(`/export/${id}`)
}

export function deleteExport(id: number) {
  return http.delete(`/export/${id}`)
}

export function batchDeleteExports(ids: number[]) {
  return http.post<any, { deleted: number }>('/export/batch-delete', { ids })
}

export function downloadExport(id: number) {
  return `${http.defaults.baseURL}/export/${id}/download`
}

/** 带认证头的文件流下载 */
export async function downloadExportFile(id: number): Promise<Blob> {
  const resp = await http.get(`/export/${id}/download`, {
    responseType: 'blob'
  })
  return resp as any
}

/** 获取导出文件内容文本（用于在线预览） */
export async function previewExportContent(id: number): Promise<string> {
  const resp = await http.get(`/export/${id}/content`, {
    responseType: 'text'
  })
  return resp as any
}
