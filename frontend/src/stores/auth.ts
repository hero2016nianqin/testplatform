import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import router from '@/router'

// 与后端 app/config/constants.py ROLE_HIERARCHY 保持一致（权限等级，>= 比较）
const ROLE_HIERARCHY: Record<string, number> = {
  operator: 0,
  process: 1,
  developer: 2,
  equipment_developer: 2,
  fd_developer: 2,
  duxingqi_developer: 2,
  trx_developer: 2,
  algorithm_developer: 2,
  power_developer: 2,
  board_software_developer: 2,
  ict_developer: 2,
  product_se: 2,
  equipment_manager: 3,
  equipment_test_manager: 3,
  super_admin: 4,
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<any>(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!user.value)
  const roleLevel = computed(() => ROLE_HIERARCHY[user.value?.role] ?? -1)

  function hasRole(minRole: string): boolean {
    return roleLevel.value >= (ROLE_HIERARCHY[minRole] ?? 99)
  }

  async function fetchCurrentUser() {
    try {
      const res = await authApi.getCurrentUser()
      user.value = res.data
    } catch {
      user.value = null
    }
  }

  async function login(username: string, password: string) {
    loading.value = true
    try {
      const res = await authApi.login({ username, password })
      user.value = res.data
      await router.push('/')
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      user.value = null
      await router.push('/login')
    }
  }

  return { user, loading, isLoggedIn, roleLevel, hasRole, fetchCurrentUser, login, logout }
})
