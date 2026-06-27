import { http } from '.'
import type { Dataset, DatasetItemsPage } from '@/types'

export function listDatasets() {
  return http.get<any, Dataset[]>('/datasets')
}

export function createDataset(payload: { name: string; description?: string }) {
  return http.post<any, Dataset>('/datasets', payload)
}

export function getDataset(id: number) {
  return http.get<any, Dataset>(`/datasets/${id}`)
}

export function deleteDataset(id: number) {
  return http.delete(`/datasets/${id}`)
}

export function uploadDatasetFile(id: number, file: File) {
  const form = new FormData()
  form.append('file', file)
  return http.post<any, Dataset>(`/datasets/${id}/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function getDatasetItems(id: number, params: { page: number; size: number }) {
  return http.get<any, DatasetItemsPage>(`/datasets/${id}/items`, { params })
}

export function mapFields(id: number, mapping: Record<string, string>) {
  return http.post<any, Dataset>(`/datasets/${id}/map-fields`, { mapping })
}