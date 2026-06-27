import { http } from '.'
import type { LoginResult, User } from '@/types'

export function login(username: string, password: string) {
  return http.post<any, LoginResult>('/auth/login', { username, password })
}

export function logout() {
  return http.post('/auth/logout')
}

export function fetchMe() {
  return http.get<any, User>('/auth/me')
}

export function listUsers() {
  return http.get<any, User[]>('/users')
}

export function createUser(payload: Partial<User> & { password: string }) {
  return http.post<any, User>('/users', payload)
}

export function updateUser(id: number, payload: Partial<User>) {
  return http.put<any, User>(`/users/${id}`, payload)
}

export function deleteUser(id: number) {
  return http.delete(`/users/${id}`)
}