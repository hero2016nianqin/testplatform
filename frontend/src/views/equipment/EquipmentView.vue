<template>
  <div class="min-w-0">
    <div class="flex items-center gap-2 mb-6">
      <el-icon :size="26" color="var(--el-color-primary)"><Cpu /></el-icon>
      <div>
        <h1 class="section-title !mb-0 !border-0 !pl-0 text-xl" style="font-weight:700;font-size:1.25rem">线体装备</h1>
        <div class="section-subtitle mt-0.5" style="font-weight:600;font-size:0.875rem">工厂 / 线体 / 工站层级管理</div>
      </div>
    </div>
    <div class="flex gap-4 h-full">
    <div class="w-72 flex-shrink-0">
      <el-card shadow="hover" class="h-full">
        <template #header>
          <div class="flex items-center justify-between">
            <span class="font-bold">装备层级</span>
            <el-button type="primary" size="small" @click="openFactoryDialog()">
              <el-icon class="mr-1"><Plus /></el-icon>新建厂区
            </el-button>
          </div>
        </template>
        <el-tree
          ref="treeRef"
          :data="treeData"
          :props="treeProps"
          node-key="id"
          :load="loadNode"
          lazy
          highlight-current
          @node-click="handleNodeClick"
          :expand-on-click-node="false"
        >
          <template #default="{ node, data }">
            <span class="flex items-center gap-1 text-sm" :class="{ 'font-bold': data.type === 'factory' }">
              <el-icon v-if="data.type === 'factory'"><OfficeBuilding /></el-icon>
              <el-icon v-else-if="data.type === 'line'"><Connection /></el-icon>
              <el-icon v-else><Monitor /></el-icon>
              {{ data.label }}
            </span>
          </template>
        </el-tree>
      </el-card>
    </div>

    <!-- Right: Content -->
    <div class="flex-1 min-w-0">
      <el-card shadow="hover" class="app-card-hover">
        <template #header>
          <div class="flex items-center justify-between">
            <span class="font-bold">{{ rightTitle }}</span>
            <div class="flex gap-2">
              <el-button
                v-if="selectedLine"
                size="small"
                type="primary"
                @click="openStationDialog()"
              >
                <el-icon class="mr-1"><Plus /></el-icon>新建工站
              </el-button>
              <el-button
                v-if="selectedFactory"
                size="small"
                @click="openLineDialog()"
              >
                <el-icon class="mr-1"><Plus /></el-icon>新建线体
              </el-button>
              <el-button
                v-if="selectedStation"
                size="small"
                @click="$router.push(`/station/${selectedStation.id}`)"
              >
                测试执行
              </el-button>
            </div>
          </div>
        </template>

        <!-- No selection -->
        <div v-if="!selectedFactory && !selectedLine && !selectedStation" class="text-center py-16 text-gray-400">
          请从左侧树中选择厂区、线体或工站
        </div>

        <!-- Factory selected (show lines table) -->
        <el-table v-else-if="selectedFactory && !selectedLine" :data="currentLines" stripe v-loading="linesLoading" style="width: 100%">
          <el-table-column type="index" label="#" width="50" />
          <el-table-column prop="name" label="线体名称" />
          <el-table-column prop="code" label="编码" width="120" />
          <el-table-column prop="description" label="描述" show-overflow-tooltip />
          <el-table-column prop="created_by" label="创建人" width="100" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="openLineDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDeleteLine(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- Line selected (show stations table) -->
        <el-table v-else-if="selectedLine" :data="currentStations" stripe v-loading="stationsLoading" style="width: 100%">
          <el-table-column type="index" label="#" width="50" />
          <el-table-column prop="name" label="工站名称" />
          <el-table-column prop="process_type" label="工序" width="80" />
          <el-table-column prop="workstation" label="工位" width="80" />
          <el-table-column prop="deployed_version" label="部署版本" width="100" />
          <el-table-column prop="latest_version" label="最新版本" width="100" />
          <el-table-column label="版本状态" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.needs_update" type="warning" size="small">可更新</el-tag>
              <el-tag v-else type="success" size="small">已是最新</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="260" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click="$router.push(`/station/${row.id}`)">测试</el-button>
              <el-button size="small" @click="$router.push(`/station-settings/${row.id}`)">配置</el-button>
              <el-button size="small" @click="openStationDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDeleteStation(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- Factory Dialog -->
    <FormDialog
      v-model:visible="factoryDialog.visible"
      :title="factoryDialog.isEdit ? '编辑厂区' : '新建厂区'"
      :form-data="factoryForm"
      :rules="factoryRules"
      :submitting="factorySubmitting"
      @submit="submitFactory"
    >
      <template #default="{ form }">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="100" />
        </el-form-item>
        <el-form-item label="编码" prop="code">
          <el-input v-model="form.code" maxlength="50" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
      </template>
    </FormDialog>

    <!-- Line Dialog -->
    <FormDialog
      v-model:visible="lineDialog.visible"
      :title="lineDialog.isEdit ? '编辑线体' : '新建线体'"
      :form-data="lineForm"
      :rules="lineRules"
      :submitting="lineSubmitting"
      @submit="submitLine"
    >
      <template #default="{ form }">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="100" />
        </el-form-item>
        <el-form-item label="编码" prop="code">
          <el-input v-model="form.code" maxlength="50" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="场景" prop="scenario">
          <el-input v-model="form.scenario" />
        </el-form-item>
        <el-form-item label="创建人" prop="created_by">
          <el-input v-model="form.created_by" />
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
      </template>
    </FormDialog>

    <!-- Station Dialog -->
    <FormDialog
      v-model:visible="stationDialog.visible"
      :title="stationDialog.isEdit ? '编辑工站' : '新建工站'"
      :form-data="stationForm"
      :rules="stationRules"
      :submitting="stationSubmitting"
      @submit="submitStation"
      width="600px"
    >
      <template #default="{ form }">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="100" />
        </el-form-item>
        <el-form-item label="装备定义" prop="definition_id" v-if="!stationDialog.isEdit">
          <el-select v-model="form.definition_id" placeholder="选择装备定义" class="w-full">
            <el-option
              v-for="d in definitions"
              :key="d.id"
              :label="`${d.name} (v${d.current_version})`"
              :value="d.id"
            />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="工序" prop="process_type">
              <el-select v-model="form.process_type" class="w-full">
                <el-option label="FT（终测）" value="FT" />
                <el-option label="老化（Burn In）" value="老化" />
                <el-option label="ORT（可靠性）" value="ORT" />
                <el-option label="SMT（贴片）" value="SMT" />
                <el-option label="Assembly（组装）" value="Assembly" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="工位" prop="workstation">
              <el-select v-model="form.workstation" class="w-full">
                <el-option v-for="i in 5" :key="i" :label="`MP${i}`" :value="`MP${i}`" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="执行器" prop="actuator">
          <el-input v-model="form.actuator" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="硬件编码" prop="hardware_code">
              <el-input v-model="form.hardware_code" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="软件编码" prop="software_code">
              <el-input v-model="form.software_code" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="创建人" prop="created_by">
          <el-input v-model="form.created_by" />
      </el-form-item>
    </template>
    </FormDialog>
  </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { stationApi } from '@/api/station'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { ElTree } from 'element-plus'
import FormDialog from '@/components/FormDialog.vue'

const treeRef = ref<InstanceType<typeof ElTree>>()
const treeData = ref<any[]>([])

const treeProps = {
  children: 'children',
  label: 'label',
  isLeaf: (data: any) => data.type === 'station',
}

const selectedFactory = ref<any>(null)
const selectedLine = ref<any>(null)
const selectedStation = ref<any>(null)
const currentLines = ref<any[]>([])
const currentStations = ref<any[]>([])
const linesLoading = ref(false)
const stationsLoading = ref(false)
const definitions = ref<any[]>([])

const rightTitle = computed(() => {
  if (selectedStation.value) return `工站: ${selectedStation.value.name}`
  if (selectedLine.value) return `线体: ${selectedLine.value.name}`
  if (selectedFactory.value) return `厂区: ${selectedFactory.value.name}`
  return '装备管理'
})

// ── Tree ──
async function loadNode(node: any, resolve: (data: any[]) => void) {
  if (node.level === 0) {
    const res = await stationApi.listFactories()
    const data = (res.data || []).map((f: any) => ({
      id: `factory-${f.id}`,
      type: 'factory',
      label: f.name,
      raw: f,
      children: [],
    }))
    resolve(data)
    return
  }

  const data = node.data
  if (data.type === 'factory') {
    const res = await stationApi.listLines(data.raw.id)
    const lines = (res.data || []).map((l: any) => ({
      id: `line-${l.id}`,
      type: 'line',
      label: l.name,
      raw: l,
      children: [],
    }))
    resolve(lines)
  } else if (data.type === 'line') {
    const res = await stationApi.listStations(data.raw.id)
    const stations = (res.data || []).map((s: any) => ({
      id: `station-${s.id}`,
      type: 'station',
      label: s.name,
      raw: s,
      isLeaf: true,
    }))
    resolve(stations)
  } else {
    resolve([])
  }
}

async function refreshTree() {
  treeData.value = []
}

async function refreshNode(type: string, id: number) {
  const nodeId = `${type}-${id}`
  const node = treeRef.value?.getNode(nodeId)
  if (node) {
    node.loaded = false
    node.expand()
  }
}

function handleNodeClick(data: any) {
  selectedFactory.value = null
  selectedLine.value = null
  selectedStation.value = null

  if (data.type === 'factory') {
    selectedFactory.value = data.raw
    loadLines(data.raw.id)
  } else if (data.type === 'line') {
    selectedLine.value = data.raw
    loadStations(data.raw.id)
  } else if (data.type === 'station') {
    selectedStation.value = data.raw
  }
}

async function loadLines(factoryId: number) {
  linesLoading.value = true
  try {
    const res = await stationApi.listLines(factoryId)
    currentLines.value = res.data || []
  } finally {
    linesLoading.value = false
  }
}

async function loadStations(lineId: number) {
  stationsLoading.value = true
  try {
    const res = await stationApi.listStations(lineId)
    currentStations.value = res.data || []
  } finally {
    stationsLoading.value = false
  }
}

// ── Factory CRUD ──
const factoryDialog = reactive({ visible: false, isEdit: false, editId: 0 })
const factorySubmitting = ref(false)

const factoryForm = reactive({
  name: '', code: '', description: '', sort_order: 0,
})

const factoryRules = {
  name: [{ required: true, message: '请输入厂区名称', trigger: 'blur' }],
}

function openFactoryDialog(row?: any) {
  if (row) {
    factoryDialog.isEdit = true
    factoryDialog.editId = row.id
    Object.assign(factoryForm, {
      name: row.name, code: row.code || '',
      description: row.description || '', sort_order: row.sort_order || 0,
    })
  } else {
    factoryDialog.isEdit = false
    factoryDialog.editId = 0
    Object.assign(factoryForm, { name: '', code: '', description: '', sort_order: 0 })
  }
  factoryDialog.visible = true
}

async function submitFactory() {
  factorySubmitting.value = true
  try {
    if (factoryDialog.isEdit) {
      await stationApi.updateFactory(factoryDialog.editId, factoryForm)
      ElMessage.success('厂区更新成功')
    } else {
      await stationApi.createFactory(factoryForm)
      ElMessage.success('厂区创建成功')
    }
    factoryDialog.visible = false
    await refreshTree()
  } finally {
    factorySubmitting.value = false
  }
}

async function handleDeleteFactory(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除厂区 "${row.name}"？`, '确认')
    await stationApi.deleteFactory(row.id)
    ElMessage.success('厂区已删除')
    await refreshTree()
  } catch { /* cancelled */ }
}

// ── Line CRUD ──
const lineDialog = reactive({ visible: false, isEdit: false, editId: 0 })
const lineSubmitting = ref(false)

const lineForm = reactive({
  factory_id: 0, name: '', code: '', description: '', scenario: '', created_by: '', sort_order: 0,
})

const lineRules = {
  name: [{ required: true, message: '请输入线体名称', trigger: 'blur' }],
}

function openLineDialog(row?: any) {
  if (row) {
    lineDialog.isEdit = true
    lineDialog.editId = row.id
    Object.assign(lineForm, {
      factory_id: row.factory_id, name: row.name, code: row.code || '',
      description: row.description || '', scenario: row.scenario || '',
      created_by: row.created_by || '', sort_order: row.sort_order || 0,
    })
  } else {
    lineDialog.isEdit = false
    lineDialog.editId = 0
    Object.assign(lineForm, {
      factory_id: selectedFactory.value?.id || 0,
      name: '', code: '', description: '', scenario: '', created_by: '', sort_order: 0,
    })
  }
  lineDialog.visible = true
}

async function submitLine() {
  lineSubmitting.value = true
  try {
    if (lineDialog.isEdit) {
      await stationApi.updateLine(lineDialog.editId, lineForm)
      ElMessage.success('线体更新成功')
    } else {
      await stationApi.createLine(lineForm)
      ElMessage.success('线体创建成功')
    }
    lineDialog.visible = false
    if (selectedFactory.value) await loadLines(selectedFactory.value.id)
    await refreshNode('factory', lineForm.factory_id)
  } finally {
    lineSubmitting.value = false
  }
}

async function handleDeleteLine(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除线体 "${row.name}"？`, '确认')
    await stationApi.deleteLine(row.id)
    ElMessage.success('线体已删除')
    if (selectedFactory.value) await loadLines(selectedFactory.value.id)
  } catch { /* cancelled */ }
}

// ── Station CRUD ──
const stationDialog = reactive({ visible: false, isEdit: false, editId: 0 })
const stationSubmitting = ref(false)

const stationForm = reactive({
  line_id: 0, definition_id: null as number | null, name: '', code: '',
  description: '', process_type: '', workstation: '', actuator: '',
  hardware_code: '', software_code: '', created_by: '',
})

const stationRules = {
  name: [{ required: true, message: '请输入工站名称', trigger: 'blur' }],
  definition_id: [{ required: true, message: '请选择装备定义', trigger: 'change' }],
}

function openStationDialog(row?: any) {
  if (row) {
    stationDialog.isEdit = true
    stationDialog.editId = row.id
    Object.assign(stationForm, {
      line_id: row.line_id, definition_id: row.definition_id, name: row.name,
      code: row.code || '', description: row.description || '',
      process_type: row.process_type || '', workstation: row.workstation || '',
      actuator: row.actuator || '', hardware_code: row.hardware_code || '',
      software_code: row.software_code || '', created_by: row.created_by || '',
    })
  } else {
    stationDialog.isEdit = false
    stationDialog.editId = 0
    Object.assign(stationForm, {
      line_id: selectedLine.value?.id || 0, definition_id: null,
      name: '', code: '', description: '', process_type: '', workstation: '',
      actuator: '', hardware_code: '', software_code: '', created_by: '',
    })
  }
  stationDialog.visible = true
}

async function submitStation() {
  stationSubmitting.value = true
  try {
    if (stationDialog.isEdit) {
      await stationApi.updateStation(stationDialog.editId, stationForm)
      ElMessage.success('工站更新成功')
    } else {
      await stationApi.createStation(stationForm)
      ElMessage.success('工站创建成功')
    }
    stationDialog.visible = false
    if (selectedLine.value) await loadStations(selectedLine.value.id)
    await refreshNode('line', stationForm.line_id)
  } finally {
    stationSubmitting.value = false
  }
}

async function handleDeleteStation(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除工站 "${row.name}"？`, '确认')
    await stationApi.deleteStation(row.id)
    ElMessage.success('工站已删除')
    if (selectedLine.value) await loadStations(selectedLine.value.id)
  } catch { /* cancelled */ }
}

onMounted(async () => {
  const res = await stationApi.listDefinitions()
  definitions.value = res.data || []
})
</script>
