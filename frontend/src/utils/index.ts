export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  const m = Math.floor(ms / 60000)
  const s = Math.round((ms % 60000) / 1000)
  return `${m}m${s}s`
}

export function slotStatusColor(status: string): string {
  const map: Record<string, string> = {
    idle: '#909399',
    testing: '#409EFF',
    pass: '#67C23A',
    fail: '#F56C6C',
    disabled: '#C0C4CC',
  }
  return map[status] || '#909399'
}

export function slotStatusLabel(status: string): string {
  const map: Record<string, string> = {
    idle: '空闲',
    testing: '测试中',
    pass: '通过',
    fail: '失败',
    disabled: '禁用',
  }
  return map[status] || status
}

export function runStatusTag(status: string): string {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

export const formatTime = formatDate
