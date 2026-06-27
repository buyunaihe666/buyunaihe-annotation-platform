import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiEnvelope } from '@/types'

const baseURL = '/api'

export const http = axios.create({
  baseURL,
  timeout: 60000
})

const TOKEN_KEY = 'buyunaihe_token'
let routerPush: ((path: string) => void) | null = null

export function setRouterPush(fn: (path: string) => void) {
  routerPush = fn
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (resp: AxiosResponse<ApiEnvelope>) => {
    const body = resp.data
    if (body && typeof body.code === 'number') {
      if (body.code !== 0) {
        ElMessage.error(body.message || '请求失败')
        return Promise.reject(new Error(body.message || '请求失败'))
      }
      return body.data as any
    }
    return body as any
  },
  (err: AxiosError<ApiEnvelope>) => {
    if (err.response?.status === 401) {
      clearToken()
      const push = routerPush
      if (push) push('/login')
      return Promise.reject(err)
    }
    const msg = err.response?.data?.message || err.message || '网络错误'
    ElMessage.error(msg)
    return Promise.reject(err)
  }
)

export function rawHttp() {
  return http
}

export * from './auth'
export * from './template'
export * from './dataset'
export * from './task'
export * from './annotation'
export * from './review'
export * from './export'
export * from './stats'