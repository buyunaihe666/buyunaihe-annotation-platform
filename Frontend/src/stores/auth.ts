import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types'
import * as authApi from '@/api/auth'
import { clearToken, setToken, getToken } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getToken())
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const role = computed(() => user.value?.role_code)

  async function login(username: string, password: string) {
    const res = await authApi.login(username, password)
    token.value = res.token
    user.value = res.user
    setToken(res.token)
    return res
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch {}
    token.value = null
    user.value = null
    clearToken()
  }

  async function fetchMe() {
    if (!token.value) return null
    try {
      const me = await authApi.fetchMe()
      user.value = me
      return me
    } catch (e) {
      token.value = null
      user.value = null
      clearToken()
      throw e
    }
  }

  return { token, user, isLoggedIn, role, login, logout, fetchMe }
})