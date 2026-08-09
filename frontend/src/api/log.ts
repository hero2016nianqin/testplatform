import api from './index'

export const logApi = {
  list(params: any) {
    return api.get('/logs', { params })
  },
  stats(days = 30) {
    return api.get('/logs/stats', { params: { days } })
  },
  exportLogs(params: any) {
    return api.get('/logs/export', { params, responseType: 'blob' })
  },
}
