import { http } from '.'
import type { Task, AnnotationItemResponse } from '@/types'

export function getSquare(params?: { status?: string; keyword?: string; tab?: string }) {
  return http.get<any, Task[]>('/annotation/square', { params })
}

export function claimItem(taskId: number, count: number = 1) {
  return http.post<any, { task_item_ids: number[]; task_item_id: number; claimed_count: number }>(
    `/annotation/tasks/${taskId}/claim`,
    null,
    { params: { count } }
  )
}

export function getAnnotationItem(itemId: number) {
  return http.get<any, AnnotationItemResponse>(`/annotation/items/${itemId}`)
}

export function saveDraft(itemId: number, result: Record<string, any>) {
  return http.put<any, { result: Record<string, any> }>(
    `/annotation/items/${itemId}/draft`,
    { result }
  )
}

export function submitItem(itemId: number, result: Record<string, any>) {
  return http.post<any, { result: Record<string, any> }>(
    `/annotation/items/${itemId}/submit`,
    { result }
  )
}

export function requestSuggestion(itemId: number) {
  return http.post<any, { suggestion_id: string }>(
    `/annotation/items/${itemId}/ai-suggestion`
  )
}

export function getSuggestion(suggestionId: string) {
  return http.get<any, { status: string; suggestion: any }>(
    `/annotation/suggestions/${suggestionId}`
  )
}