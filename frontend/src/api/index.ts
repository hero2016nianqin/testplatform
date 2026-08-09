import axios, { type AxiosAdapter } from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  withCredentials: true,
})

// resolve string adapter name(s) to actual function
const _adapterNames = axios.defaults.adapter as string[]
const _defaultAdapter = (() => {
  for (const name of _adapterNames) {
    const fn = (axios as any).getAdapter(name, {})
    if (typeof fn === 'function') return fn as AxiosAdapter
  }
  throw new Error('no suitable axios adapter found')
})()

// dedup in-flight GET requests — share the same axios adapter promise
const inflight = new Map<string, Promise<any>>()

api.defaults.adapter = (config) => {
  if (config.method?.toLowerCase() === 'get') {
    const key = `${config.url}|${JSON.stringify(config.params || {})}`
    const pending = inflight.get(key)
    if (pending) return pending
    const promise = _defaultAdapter(config).finally(() => inflight.delete(key))
    inflight.set(key, promise)
    return promise
  }
  return _defaultAdapter(config)
}

api.interceptors.response.use(
  (response) => {
    // Skip JSON parsing for blob/arraybuffer downloads (e.g., file export)
    if (response.config.responseType === 'blob' || response.config.responseType === 'arraybuffer') {
      return response.data
    }
    const data = response.data
    if (data.code !== 0) {
      ElMessage.error(data.message || '请求失败')
      return Promise.reject(new Error(data.message))
    }
    return data
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      if (status === 403) {
        ElMessage.error('权限不足')
      } else if (status === 404) {
        ElMessage.error('资源不存在')
      } else {
        ElMessage.error(data?.message || `请求失败 (${status})`)
      }
    } else if (error.request) {
      ElMessage.error('网络异常，请检查连接')
    }
    return Promise.reject(error)
  },
)

export default api