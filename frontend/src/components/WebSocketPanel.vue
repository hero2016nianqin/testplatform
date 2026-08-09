<template>
  <div class="log-panel bg-gray-900 text-green-400 rounded p-2 text-xs" ref="panelRef">
    <div v-for="(log, i) in logs" :key="i" class="leading-5">
      <span class="text-gray-500 mr-2">{{ log.time }}</span>
      <span :class="logColor(log.level)">{{ log.message }}</span>
    </div>
    <div v-if="logs.length === 0" class="text-gray-600">等待测试事件...</div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'

const props = defineProps<{
  stationId?: number
}>()

const logs = ref<Array<{ time: string; level: string; message: string }>>([])
const panelRef = ref<HTMLElement | null>(null)

function addLog(level: string, message: string) {
  const now = new Date()
  const time = now.toLocaleTimeString('zh-CN', { hour12: false })
  logs.value.push({ time, level, message })
  if (logs.value.length > 200) {
    logs.value.shift()
  }
  nextTick(() => {
    if (panelRef.value) {
      panelRef.value.scrollTop = panelRef.value.scrollHeight
    }
  })
}

function logColor(level: string): string {
  const map: Record<string, string> = {
    info: 'text-blue-400',
    success: 'text-green-400',
    warn: 'text-yellow-400',
    error: 'text-red-400',
  }
  return map[level] || 'text-white'
}

defineExpose({ addLog })
</script>
