import { http } from '.'
import type {
  Task,
  TaskProgress,
  TaskAssignment,
  TaskItem
} from '@/types'

export function listTasks(params?: { status?: string; keyword?: string }) {
  return http.get<any, Task[]>('/tasks', { params })
}

export function createTask(payload: Partial<Task>) {
  return http.post<any, Task>('/tasks', payload)
}

export function getTask(id: number) {
  return http.get<any, Task>(`/tasks/${id}`)
}

export function updateTask(id: number, payload: Partial<Task>) {
  return http.put<any, Task>(`/tasks/${id}`, payload)
}

export function deleteTask(id: number) {
  return http.delete(`/tasks/${id}`)
}

export function publishTask(id: number) {
  return http.post<any, Task>(`/tasks/${id}/publish`)
}

export function pauseTask(id: number) {
  return http.post<any, Task>(`/tasks/${id}/pause`)
}

export function completeTask(id: number) {
  return http.post<any, Task>(`/tasks/${id}/complete`)
}

export function getTaskProgress(id: number) {
  return http.get<any, TaskProgress>(`/tasks/${id}/progress`)
}

export function assignTask(id: number, assignments: { user_id: number; role: string }[]) {
  return http.post(`/tasks/${id}/assign`, { assignments })
}

export function getAssignees(id: number) {
  return http.get<any, TaskAssignment[]>(`/tasks/${id}/assignees`)
}

export function getTaskItems(
  id: number,
  params: { status?: string; page?: number; size?: number }
) {
  return http.get<any, { items: TaskItem[]; total: number }>(`/tasks/${id}/items`, {
    params
  })
}

export function getTaskItem(id: number, itemId: number) {
  return http.get<any, any>(`/tasks/${id}/items/${itemId}`)
}