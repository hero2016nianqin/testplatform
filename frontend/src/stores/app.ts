import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const currentFactoryId = ref<number | null>(null)
  const currentFactoryName = ref('')
  const wsConnected = ref(false)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setFactory(id: number | null, name: string) {
    currentFactoryId.value = id
    currentFactoryName.value = name
    sessionStorage.setItem('factoryId', String(id ?? ''))
    sessionStorage.setItem('factoryName', name)
  }

  function loadFactory() {
    const id = sessionStorage.getItem('factoryId')
    const name = sessionStorage.getItem('factoryName')
    if (id) currentFactoryId.value = Number(id)
    if (name) currentFactoryName.value = name
  }

  return {
    sidebarCollapsed, currentFactoryId, currentFactoryName, wsConnected,
    toggleSidebar, setFactory, loadFactory,
  }
})
