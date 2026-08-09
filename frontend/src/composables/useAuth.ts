import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function useAuth() {
  const store = useAuthStore()

  const isLoggedIn = computed(() => store.isLoggedIn)
  const user = computed(() => store.user)
  const roleLevel = computed(() => store.roleLevel)

  function canAccess(minRole: string): boolean {
    return store.hasRole(minRole)
  }

  return { isLoggedIn, user, roleLevel, canAccess }
}
