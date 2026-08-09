import api from './index'

export const testApi = {
  listItems(category?: string) {
    return api.get('/tests/items', { params: { category } })
  },
  createItem(data: any) {
    return api.post('/tests/items', data)
  },
  updateItem(id: number, data: any) {
    return api.put(`/tests/items/${id}`, data)
  },
  deleteItem(id: number) {
    return api.delete(`/tests/items/${id}`)
  },
  listTemplates(category?: string) {
    return api.get('/tests/templates', { params: { category } })
  },
  createTemplate(data: any) {
    return api.post('/tests/templates', data)
  },
  updateTemplate(id: number, data: any) {
    return api.put(`/tests/templates/${id}`, data)
  },
  deleteTemplate(id: number) {
    return api.delete(`/tests/templates/${id}`)
  },
  listSequences() {
    return api.get('/tests/sequences')
  },
  getSequence(id: number) {
    return api.get(`/tests/sequences/${id}`)
  },
  createSequence(data: any) {
    return api.post('/tests/sequences', data)
  },
  updateSequence(id: number, data: any) {
    return api.put(`/tests/sequences/${id}`, data)
  },
  deleteSequence(id: number) {
    return api.delete(`/tests/sequences/${id}`)
  },
  listRuns(params: any) {
    return api.get('/tests/runs', { params })
  },
  createRun(data: any) {
    return api.post('/tests/runs', data)
  },
  updateRun(id: number, data: any) {
    return api.put(`/tests/runs/${id}`, data)
  },
  submitResult(runId: number, data: any) {
    return api.post(`/tests/runs/${runId}/results`, data)
  },
  getRecords(params: any) {
    return api.get('/tests/records', { params })
  },
  scanTest(params: any) {
    return api.post('/tests/scan', null, { params })
  },
}
