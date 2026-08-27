import { ref, onUnmounted } from 'vue'

interface WsMessage {
  event: string
  data: any
}

type MessageHandler = (msg: WsMessage) => void

export function useWebSocket(stationId?: number) {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  const listeners = new Map<string, Set<MessageHandler>>()
  let heartbeatTimer: number | null = null
  let reconnectTimer: number | null = null
  let intentionalDisconnect = false

  function getUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    if (stationId) {
      return `${protocol}//${host}/ws/stations/${stationId}`
    }
    return `${protocol}//${host}/ws/global`
  }

  function connect() {
    if (ws.value && (ws.value.readyState === WebSocket.OPEN || ws.value.readyState === WebSocket.CONNECTING)) return

    const url = getUrl()
    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      connected.value = true
      startHeartbeat()
    }

    ws.value.onclose = () => {
      connected.value = false
      stopHeartbeat()
      if (!intentionalDisconnect) {
        scheduleReconnect()
      }
    }

    ws.value.onerror = () => {
      connected.value = false
    }

    ws.value.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data)
        if (msg.event === 'ping') {
          ws.value?.send(JSON.stringify({ event: 'pong' }))
          return
        }
        const handlers = listeners.get(msg.event)
        if (handlers) {
          handlers.forEach((h) => h(msg))
        }
      } catch {
        // ignore
      }
    }
  }

  function disconnect() {
    intentionalDisconnect = true
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    stopHeartbeat()
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    connected.value = false
    intentionalDisconnect = false
  }

  function on(event: string, handler: MessageHandler) {
    if (!listeners.has(event)) {
      listeners.set(event, new Set())
    }
    listeners.get(event)!.add(handler)
  }

  function off(event: string, handler: MessageHandler) {
    listeners.get(event)?.delete(handler)
  }

  function startHeartbeat() {
    stopHeartbeat()
    heartbeatTimer = window.setInterval(() => {
      if (ws.value?.readyState === WebSocket.OPEN) {
        ws.value.send(JSON.stringify({ event: 'pong' }))
      }
    }, 25000)
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer) return
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null
      connect()
    }, 3000)
  }

  onUnmounted(() => {
    disconnect()
  })

  return { ws, connected, connect, disconnect, on, off }
}
