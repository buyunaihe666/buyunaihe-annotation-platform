import { http } from '.'
import type { Task, ReviewItemResponse, AiReport } from '@/types'

export function listReviewTasks(params?: { keyword?: string }) {
  return http.get<any, Task[]>('/review/tasks', { params })
}

export function listReviewItems(
  taskId: number,
  params: { status?: string; page?: number; size?: number }
) {
  return http.get<any, { items: any[]; total: number }>(
    `/review/tasks/${taskId}/items`,
    { params }
  )
}

export function getReviewItem(itemId: number) {
  return http.get<any, ReviewItemResponse>(`/review/items/${itemId}`)
}

export function getReviewAiReport(itemId: number) {
  return http.get<any, AiReport>(`/review/items/${itemId}/ai-report`)
}

export function submitDecision(
  itemId: number,
  decision: string,
  comment: string
) {
  return http.post<any, any>(`/review/items/${itemId}/decision`, {
    decision,
    comment
  })
}

export function submitModifyAndPass(
  itemId: number,
  body: { decision: string; comment: string }
) {
  return http.post<any, any>(`/review/items/${itemId}/modify-and-pass`, body)
}