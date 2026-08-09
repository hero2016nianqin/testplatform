import api from './index'

export const authApi = {
  login(data: { username: string; password: string }) {
    return api.post('/auth/login', data)
  },
  logout() {
    return api.post('/auth/logout')
  },
  getCurrentUser() {
    return api.get('/auth/me')
  },
  listUsers(page = 1, pageSize = 20, role?: string, status?: string) {
    const params: Record<string, any> = { page, page_size: pageSize }
    if (role) params.role = role
    if (status) params.status = status
    return api.get('/auth/users', { params })
  },
  createUser(data: any) {
    return api.post('/auth/users', data)
  },
  updateUser(userId: number, data: any) {
    return api.put(`/auth/users/${userId}`, data)
  },
  deleteUser(userId: number) {
    return api.delete(`/auth/users/${userId}`)
  },
  resetPassword(userId: number, data: { new_password: string }) {
    return api.put(`/auth/users/${userId}/reset-password`, data)
  },
  updateDomains(userId: number, data: { domains: string[] }) {
    return api.put(`/auth/users/${userId}/domains`, data)
  },
  register(data: {
    username: string
    display_name: string
    password: string
    department: string
    requested_role: string
    requested_domains?: string[]
    justification?: string
  }) {
    return api.post('/auth/register', data)
  },
  listRegistrations(page = 1, pageSize = 20) {
    return api.get('/auth/registrations', { params: { page, page_size: pageSize } })
  },
  approveRegistration(regId: number, data: { approved_domains?: string[] }) {
    return api.put(`/auth/registrations/${regId}/approve`, {}, { params: data.approved_domains ? { approved_domains: data.approved_domains.join(',') } : undefined })
  },
  rejectRegistration(regId: number, data: { comment: string }) {
    return api.put(`/auth/registrations/${regId}/reject`, {}, { params: { comment: data.comment } })
  },
  listAuditLogs(page = 1, pageSize = 20, filters?: Record<string, any>) {
    return api.get('/auth/audit-logs', { params: { page, page_size: pageSize, ...filters } })
  },
}
