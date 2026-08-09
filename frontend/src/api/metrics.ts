import api from './index'

export const metricsApi = {
  // ── 指标字典库 ──
  listIndicators(params?: any) { return api.get('/metrics/indicators', { params }) },
  listAllIndicators() { return api.get('/metrics/indicators/all') },
  listIndicatorCategories() { return api.get('/metrics/indicators/categories') },
  listIndicatorDomains() { return api.get('/metrics/indicators/domains') },
  createIndicator(data: any) { return api.post('/metrics/indicators', data) },
  updateIndicator(id: number, data: any) { return api.put(`/metrics/indicators/${id}`, data) },
  saveIndicator(data: any) { return api.put('/metrics/indicators/save', data) },
  deleteIndicator(id: number) { return api.delete(`/metrics/indicators/${id}`) },

  // ── 测试项集合管理 ──
  listCollections(params?: any) { return api.get('/metrics/collections', { params }) },
  listAllCollections() { return api.get('/metrics/collections/all') },
  createCollection(data: any) { return api.post('/metrics/collections', data) },
  updateCollection(id: number, data: any) { return api.put(`/metrics/collections/${id}`, data) },
  deleteCollection(id: number) { return api.delete(`/metrics/collections/${id}`) },

  listCollectionItems(collectionId: number, version?: number) {
    const params = version !== undefined ? `?version=${version}` : ''
    return api.get(`/metrics/collections/${collectionId}/items${params}`)
  },
  createCollectionItem(collectionId: number, data: any) { return api.post(`/metrics/collections/${collectionId}/items`, data) },
  updateCollectionItem(itemId: number, data: any) { return api.put(`/metrics/collections/items/${itemId}`, data) },
  updateCollectionItemOwner(itemId: number, ownerName: string) { return api.put(`/metrics/collections/items/${itemId}/owner`, { owner_name: ownerName }) },
  deleteCollectionItem(itemId: number) { return api.delete(`/metrics/collections/items/${itemId}`) },

  // ── BOM 指标配置 ──
  getBomConfig(id: number) { return api.get(`/metrics/bom-configs/${id}`) },
  listBomConfigs(params?: any) { return api.get('/metrics/bom-configs', { params }) },
  listGroupedBomConfigs(params?: any) { return api.get('/metrics/bom-configs/grouped', { params }) },
  listBomConfigsByCode(bomCode: string) { return api.get('/metrics/bom-configs/by-code', { params: { bom_code: bomCode } }) },
  listBomCodes(params?: any) { return api.get('/metrics/bom-configs/bom-codes', { params }) },
  checkBomVersion(bomCode: string, excludeConfigId: number = 0) {
    return fetch(`/api/v1/metrics/bom-configs/check-version?bom_code=${encodeURIComponent(bomCode || '')}&exclude_config_id=${excludeConfigId || 0}`, { credentials: 'include' }).then(r => r.json())
  },
  createBomConfig(data: any) { return api.post('/metrics/bom-configs', data) },
  updateBomConfig(id: number, data: any) { return api.put(`/metrics/bom-configs/${id}`, data) },
  deleteBomConfig(id: number) { return api.delete(`/metrics/bom-configs/${id}`) },
  copyBomConfig(id: number, data: any) { return api.post(`/metrics/bom-configs/${id}/copy`, data) },
  switchBomVersion(configId: number, snapshotId: number) { return api.put(`/metrics/bom-configs/${configId}/switch-version`, null, { params: { snapshot_id: snapshotId } }) },

  getBomDomainOwners(configId: number) { return api.get(`/metrics/bom-configs/${configId}/domain-owners`) },
  updateBomDomainOwners(configId: number, data: any) { return api.put(`/metrics/bom-configs/${configId}/domain-owners`, data) },

  // ── BOM Domain Owners by BOM Code (shared across versions) ──
  getBomDomainOwnersByBomCode(bomCode: string) { return api.get('/metrics/bom-configs/domain-owners', { params: { bom_code: bomCode } }) },
  updateBomDomainOwnersByBomCode(bomCode: string, data: any) { return api.put('/metrics/bom-configs/domain-owners', data, { params: { bom_code: bomCode } }) },

  listBomIndicators(configId: number) { return api.get(`/metrics/bom-configs/${configId}/indicators`) },
  addBomIndicator(configId: number, data: any) { return api.post(`/metrics/bom-configs/${configId}/indicators`, data) },
  batchAddBomIndicators(configId: number, data: any) { return api.post(`/metrics/bom-configs/${configId}/indicators/batch`, data) },
  batchUpdateBomIndicators(configId: number, data: any) { return api.put(`/metrics/bom-configs/${configId}/indicators/batch-update`, data) },
  batchUpdateBomIndicatorStatus(configId: number, data: any) { return api.put(`/metrics/bom-configs/${configId}/indicators/batch-status`, data) },
  updateBomIndicator(indicatorId: number, data: any) { return api.put(`/metrics/bom-configs/indicators/${indicatorId}`, data) },
  deleteBomIndicator(indicatorId: number) { return api.delete(`/metrics/bom-configs/indicators/${indicatorId}`) },

  // ── 版本记录 ──
  listVersions(params?: any) { return api.get('/metrics/versions', { params }) },
  getVersionDetail(snapshotId: number) { return api.get(`/metrics/versions/${snapshotId}`) },
  rollbackVersion(snapshotId: number, data?: any) { return api.post(`/metrics/versions/${snapshotId}/rollback`, data) },
  getVersionDiff(snapshotId: number) { return api.get(`/metrics/versions/${snapshotId}/diff`) },
  diffTwoVersions(params: any) { return api.get('/metrics/versions/diff', { params }) },
  diffBaseline(configId: number) { return api.get(`/metrics/bom-configs/${configId}/diff-baseline`) },

  // ── 集合可用指标 (按集合过滤) ──
  listCollectionIndicators(collectionId: number) { return api.get(`/metrics/collections/${collectionId}/available-indicators`) },

  // ── 测试项绑定指标 (二期) ──
  listItemIndicators(itemId: number) { return api.get(`/metrics/collections/items/${itemId}/indicators`) },
  batchAddItemIndicators(itemId: number, data: any) { return api.post(`/metrics/collections/items/${itemId}/indicators/batch`, data) },
  deleteItemIndicator(indicatorId: number) { return api.delete(`/metrics/collections/items/indicators/${indicatorId}`) },

  // ── 指标引用追溯 (二期) ──
  getIndicatorReferences(indicatorId: number) { return api.get(`/metrics/indicators/${indicatorId}/references`) },

  // ── 字典库指标参数 CRUD (test_params) ──
  addIndicatorParam(indicatorId: number, data: any) { return api.post(`/metrics/indicators/${indicatorId}/params`, data) },
  updateIndicatorParam(indicatorId: number, paramKey: string, data: any) { return api.put(`/metrics/indicators/${indicatorId}/params/${encodeURIComponent(paramKey)}`, data) },
  deleteIndicatorParam(indicatorId: number, paramKey: string) { return api.delete(`/metrics/indicators/${indicatorId}/params/${encodeURIComponent(paramKey)}`) },

  // ── 脚本沙箱预览 ──
  previewIndicatorScript(indicatorId: number, data: any) { return api.post(`/metrics/indicators/${indicatorId}/script/preview`, data) },

  // ── 自定义脚本模板 ──
  listScriptTemplates(params?: any) { return api.get('/metrics/script-templates', { params }) },
  listActiveScripts() { return api.get('/metrics/script-templates/active') },
  getScriptTemplate(id: number) { return api.get(`/metrics/script-templates/${id}`) },
  createScriptTemplate(data: any) { return api.post('/metrics/script-templates', data) },
  updateScriptTemplate(id: number, data: any) { return api.put(`/metrics/script-templates/${id}`, data) },
  deleteScriptTemplate(id: number) { return api.delete(`/metrics/script-templates/${id}`) },
  toggleScriptStatus(id: number, status: number) { return api.put(`/metrics/script-templates/${id}/status`, null, { params: { status } }) },
  executeScript(data: any) { return api.post('/metrics/script-templates/execute', data) },
  validateScriptSource(data: any) { return api.post('/metrics/script-templates/validate', data) },

  // ── 联合查询 & 导出 ──
  queryIndicators(params?: any) { return api.get('/metrics/query', { params }) },
  exportIndicators(params?: any) {
    return api.post('/metrics/export', null, {
      params,
      responseType: 'blob',
      timeout: 60000,
    })
  },

  batchUpdateIndicators(data: any) { return api.put('/metrics/indicators/batch', data) },

  // ── Alert Center ──
  listAlertIndicators(params?: any) { return api.get('/metrics/indicators/alerts', { params }) },

  // ── Per-indicator Script ──
  getIndicatorScript(indicatorId: number) { return api.get(`/metrics/indicators/${indicatorId}/script`) },
  updateIndicatorScript(indicatorId: number, data: any) { return api.put(`/metrics/indicators/${indicatorId}/script`, data) },
  validateIndicatorScript(indicatorId: number, data: any) { return api.post(`/metrics/indicators/${indicatorId}/script/validate`, data) },
  resetIndicatorScript(indicatorId: number) { return api.post(`/metrics/indicators/${indicatorId}/script/reset`, {}) },

  // ── BOM Export (per-indicator script) ──
  exportBomConfig(configId: number, data: any) { return api.post(`/metrics/bom-configs/${configId}/export`, data) },
  submitReview(configId: number, data: any) { return api.post(`/metrics/bom-configs/${configId}/submit-review`, data) },
  approveReview(configId: number, data: any) { return api.post(`/metrics/bom-configs/${configId}/approve-review`, data) },
  rejectReview(configId: number, data: any) { return api.post(`/metrics/bom-configs/${configId}/reject-review`, data) },
  withdrawReview(configId: number) { return api.post(`/metrics/bom-configs/${configId}/withdraw-review`, {}) },
  archiveBom(configId: number) { return api.post(`/metrics/bom-configs/${configId}/archive`, {}) },
  createNewIteration(configId: number) { return api.post(`/metrics/bom-configs/${configId}/new-iteration`, {}) },
  exportBomExcel(configId: number) { return api.post(`/metrics/bom-configs/${configId}/export-excel`, {}) },
  exportBomDiffReport(configId: number) { return api.post(`/metrics/bom-configs/${configId}/export-diff-report`, {}) },

  // ── Per-param CRUD within BOM indicator ──
  addBomIndicatorParam(bomIndicatorId: number, data: any) { return api.post(`/metrics/bom-configs/indicators/${bomIndicatorId}/params`, data) },
  updateBomIndicatorParam(bomIndicatorId: number, paramKey: string, data: any) { return api.put(`/metrics/bom-configs/indicators/${bomIndicatorId}/params/${encodeURIComponent(paramKey)}`, data) },
  deleteBomIndicatorParam(bomIndicatorId: number, paramKey: string) { return api.delete(`/metrics/bom-configs/indicators/${bomIndicatorId}/params/${encodeURIComponent(paramKey)}`) },

  // ── All Indicators Export (per-indicator script) ──
  exportAllIndicators(data: any) { return api.post('/metrics/indicators/export', data) },

  // ── Excel Import ──
  importIndicatorsExcel(formData: FormData) {
    return api.post('/metrics/indicators/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000,
    })
  },

  // ── BOM Excel Template / Import / Export ──
  exportBomTemplate(configId: number) {
    return api.post(`/metrics/bom-configs/${configId}/export-template`, {})
  },
  exportCurrentConfig(configId: number, params?: { process_name?: string; station_name?: string }) {
    return api.post(`/metrics/bom-configs/${configId}/export-current`, params || {})
  },
  importBomConfig(configId: number, formData: FormData) {
    return api.post(`/metrics/bom-configs/${configId}/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000,
    })
  },

  // ── Reports ──
  exportDiffReport(configId: number, params?: { archived_id?: number }) {
    return api.post(`/metrics/bom-configs/${configId}/export-diff-report`, params || {})
  },
  exportPdfReport(configId: number) {
    return api.post(`/metrics/bom-configs/${configId}/export-pdf`, {})
  },

  // ── Validation ──
  validateBomConfig(configId: number) {
    return api.post(`/metrics/bom-configs/${configId}/validate`, {})
  },

  // ── 协同编辑：批量保存参数（乐观锁） ──
  batchSaveIndicatorParams(configId: number, data: any) {
    return api.put(`/metrics/bom-configs/${configId}/indicators/batch-save`, data)
  },

  // ── 协同编辑：参数变更记录 ──
  getChangeLogs(configId: number, params?: any) {
    return api.get(`/metrics/bom-configs/${configId}/change-logs`, { params })
  },
}
