import api from './index'

export const versionApi = {
  list(params: any) {
    return api.get('/versions', { params })
  },
  create(data: any) {
    return api.post('/versions', data)
  },
  get(id: number) {
    return api.get(`/versions/${id}`)
  },
  update(id: number, data: any) {
    return api.put(`/versions/${id}`, data)
  },
  deleteVersion(id: number) {
    return api.delete(`/versions/${id}`)
  },
  delist(id: number) {
    return api.post(`/versions/${id}/delist`)
  },
  restore(id: number) {
    return api.post(`/versions/${id}/restore`)
  },
  assignApprovers(id: number, data: any) {
    return api.post(`/versions/${id}/assign-approvers`, data)
  },
  submitStep(id: number, data: any) {
    return api.post(`/versions/${id}/submit-step`, data)
  },
  listSubScenarios(id: number) {
    return api.get(`/versions/${id}/sub-scenarios`)
  },
  createSubScenario(id: number, data: any) {
    return api.post(`/versions/${id}/sub-scenarios`, data)
  },
  updateSubScenario(ssId: number, data: any) {
    return api.put(`/versions/sub-scenarios/${ssId}`, data)
  },
  deleteSubScenario(ssId: number) {
    return api.delete(`/versions/sub-scenarios/${ssId}`)
  },
  listBinaries(id: number) {
    return api.get(`/versions/${id}/binaries`)
  },
  uploadBinary(id: number, data: FormData, subScenarioId?: number) {
    if (subScenarioId) {
      data.append('sub_scenario_id', String(subScenarioId))
    }
    return api.post(`/versions/${id}/binaries`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteBinary(versionId: number, fileId: number) {
    return api.delete(`/versions/${versionId}/binaries/${fileId}`)
  },
  downloadBinaryUrl(versionId: number, fileId: number) {
    return `/api/v1/versions/${versionId}/binaries/${fileId}/download`
  },
  createDeployment(id: number, data: any) {
    return api.post(`/versions/${id}/deployments`, data)
  },
  approveDeployment(deploymentId: number, data: any) {
    return api.post(`/versions/deployments/${deploymentId}/approve`, data)
  },
  executeDeployment(deploymentId: number) {
    return api.post(`/versions/deployments/${deploymentId}/execute`)
  },
  pendingApprovals() {
    return api.get('/versions/pending-approvals')
  },
  nextVersion(projectName: string) {
    return api.get('/versions/next-version', { params: { project_name: projectName } })
  },
  allUsers() {
    return api.get('/versions/all-users')
  },
  archiveConfigs() {
    return api.get('/versions/archive-configs')
  },
  subScenarioPresets() {
    return api.get('/versions/sub-scenario-presets')
  },
}
