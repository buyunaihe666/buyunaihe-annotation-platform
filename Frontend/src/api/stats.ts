import { http } from '.'
import type { StatsOverview, TaskStatsResponse, LabelerStat } from '@/types'

export function getOverview() {
  return http.get<any, StatsOverview>('/stats/overview')
}

export function getTaskStats(id: number) {
  return http.get<any, TaskStatsResponse>(`/stats/task/${id}`)
}