import api from './index'

export const stationApi = {
  listFactories() {
    return api.get('/stations/factories')
  },
  createFactory(data: any) {
    return api.post('/stations/factories', data)
  },
  updateFactory(id: number, data: any) {
    return api.put(`/stations/factories/${id}`, data)
  },
  deleteFactory(id: number) {
    return api.delete(`/stations/factories/${id}`)
  },
  listLines(factoryId?: number) {
    return api.get('/stations/lines', { params: { factory_id: factoryId } })
  },
  createLine(data: any) {
    return api.post('/stations/lines', data)
  },
  updateLine(id: number, data: any) {
    return api.put(`/stations/lines/${id}`, data)
  },
  deleteLine(id: number) {
    return api.delete(`/stations/lines/${id}`)
  },
  listStations(lineId?: number) {
    return api.get('/stations', { params: { line_id: lineId } })
  },
  createStation(data: any) {
    return api.post('/stations', data)
  },
  getStation(id: number) {
    return api.get(`/stations/${id}`)
  },
  getStationDetail(id: number) {
    return api.get(`/stations/${id}/detail`)
  },
  updateSlot(slotId: number, data: any) {
    return api.put(`/stations/slots/${slotId}`, data)
  },
  updateStation(id: number, data: any) {
    return api.put(`/stations/${id}`, data)
  },
  deleteStation(id: number) {
    return api.delete(`/stations/${id}`)
  },
  getEquipment(id: number) {
    return api.get(`/stations/${id}/equipment`)
  },
  updateEquipment(id: number, data: any) {
    return api.put(`/stations/${id}/equipment`, data)
  },
  listHardware(id: number) {
    return api.get(`/stations/${id}/hardware`)
  },
  createHardware(id: number, data: any) {
    return api.post(`/stations/${id}/hardware`, data)
  },
  updateHardware(paramId: number, data: any) {
    return api.put(`/stations/hardware/${paramId}`, data)
  },
  deleteHardware(paramId: number) {
    return api.delete(`/stations/hardware/${paramId}`)
  },
  batchReplaceHardware(id: number, data: any) {
    return api.put(`/stations/${id}/hardware/batch`, data)
  },
  getSoftware(id: number) {
    return api.get(`/stations/${id}/software`)
  },
  updateSoftware(id: number, data: any) {
    return api.put(`/stations/${id}/software`, data)
  },
  getScenario(id: number) {
    return api.get(`/stations/${id}/scenario`)
  },
  updateScenario(id: number, data: any) {
    return api.put(`/stations/${id}/scenario`, data)
  },
  getMetrics(id: number) {
    return api.get(`/stations/${id}/metrics`)
  },
  updateMetrics(id: number, data: any) {
    return api.put(`/stations/${id}/metrics`, data)
  },
  getPropertyPage(id: number) {
    return api.get(`/stations/${id}/property-page`)
  },
  updatePropertyPage(id: number, data: any) {
    return api.put(`/stations/${id}/property-page`, data)
  },
  syncVersionProps(id: number, data: any) {
    return api.put(`/stations/${id}/sync-version-props`, data)
  },
  versionCheck(id: number) {
    return api.get(`/stations/${id}/version-check`)
  },
  updateVersion(id: number) {
    return api.post(`/stations/${id}/update-version`)
  },
  getDeployedVersion(id: number, params?: any) {
    return api.get(`/stations/${id}/deployed-version`, { params })
  },
  listDeployedVersions(id: number, deployedOnly?: boolean) {
    return api.get(`/stations/${id}/deployed-versions`, { params: { deployed_only: deployedOnly } })
  },
  listDefinitions() {
    return api.get('/stations/definitions')
  },
  createDefinition(data: any) {
    return api.post('/stations/definitions', data)
  },
  updateDefinition(id: number, data: any) {
    return api.put(`/stations/definitions/${id}`, data)
  },
}
