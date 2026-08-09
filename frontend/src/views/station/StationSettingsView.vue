<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-2xl font-bold">单站配置 — #{{ stationId }}</h1>
      <el-tag v-if="stationName">{{ stationName }}</el-tag>
    </div>

    <el-card shadow="hover" v-loading="loading">
      <el-tabs v-model="activeTab">
        <!-- Tab 1: Equipment Config -->
        <el-tab-pane label="装备参数" name="equipment">
          <el-form :model="equipForm" label-width="160px" v-if="equipForm">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="装备 IP">
                  <el-input v-model="equipForm.equipment_ip" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="服务地址">
                  <el-input v-model="equipForm.equipment_service_address" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="8">
                <el-form-item label="正常测试模式">
                  <el-switch v-model="equipForm.test_mode_normal" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="验证测试模式">
                  <el-switch v-model="equipForm.test_mode_verify" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="校准测试模式">
                  <el-switch v-model="equipForm.test_mode_calibration" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="8">
                <el-form-item label="条码校验">
                  <el-switch v-model="equipForm.barcode_verify_enabled" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="自动上板">
                  <el-switch v-model="equipForm.auto_load_enabled" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="调试模式">
                  <el-switch v-model="equipForm.debug_mode_enabled" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="工序管控">
              <el-switch v-model="equipForm.process_control_enabled" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="equipSaving" @click="saveEquipment">保存装备参数</el-button>
            </el-form-item>
          </el-form>
          <div v-else class="text-center text-gray-400 py-8">加载中...</div>
        </el-tab-pane>

        <!-- Tab 2: Hardware Params -->
        <el-tab-pane label="硬件参数" name="hardware">
          <div class="mb-3 flex gap-2">
            <el-button type="primary" size="small" @click="openHardwareDialog()">新建参数</el-button>
            <el-button size="small" @click="showBatchReplace = true">批量替换</el-button>
          </div>
          <el-table :data="hardwareParams" stripe v-loading="hardwareLoading" style="width: 100%">
            <el-table-column prop="param_name" label="参数名" />
            <el-table-column prop="param_value" label="参数值" />
            <el-table-column prop="group_name" label="分组" width="120" />
            <el-table-column prop="sort_order" label="排序" width="80" />
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openHardwareDialog(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="handleDeleteHardware(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- Batch Replace Dialog -->
          <el-dialog v-model="showBatchReplace" title="批量替换硬件参数" width="600px">
            <p class="text-sm text-gray-500 mb-3">粘贴参数列表（每行一个，格式：参数名=参数值）</p>
            <el-input
              v-model="batchReplaceText"
              type="textarea"
              :rows="10"
              placeholder="power_voltage=220&#10;current_limit=10&#10;frequency=50"
            />
            <template #footer>
              <el-button @click="showBatchReplace = false">取消</el-button>
              <el-button type="primary" :loading="batchSaving" @click="submitBatchReplace">替换</el-button>
            </template>
          </el-dialog>

          <!-- Hardware Param Dialog -->
          <FormDialog
            v-model:visible="hardwareDialog.visible"
            :title="hardwareDialog.isEdit ? '编辑硬件参数' : '新建硬件参数'"
            :form-data="hardwareForm"
            :rules="{ param_name: [{ required: true, message: '请输入参数名', trigger: 'blur' }] }"
            :submitting="hardwareSubmitting"
            @submit="submitHardware"
          >
            <template #default="{ form }">
              <el-form-item label="参数名" prop="param_name">
                <el-input v-model="form.param_name" />
              </el-form-item>
              <el-form-item label="参数值" prop="param_value">
                <el-input v-model="form.param_value" />
              </el-form-item>
              <el-form-item label="分组" prop="group_name">
                <el-input v-model="form.group_name" placeholder="default" />
              </el-form-item>
              <el-form-item label="排序" prop="sort_order">
                <el-input-number v-model="form.sort_order" :min="0" />
              </el-form-item>
            </template>
          </FormDialog>
        </el-tab-pane>

        <!-- Tab 3: Software Config -->
        <el-tab-pane label="软件参数" name="software">
          <el-form :model="softForm" label-width="160px" v-if="softForm">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="项目名称">
                  <el-input v-model="softForm.project_name" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="DUT 版本">
                  <el-input v-model="softForm.dut_version" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="固件版本">
                  <el-input v-model="softForm.dut_firmware_version" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="硬件版本">
                  <el-input v-model="softForm.dut_hardware_version" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="8">
                <el-form-item label="工序">
                  <el-input v-model="softForm.process_type" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="工位">
                  <el-input v-model="softForm.workstation" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="BOM 编码">
                  <el-input v-model="softForm.bom_code" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="已选测试项">
              <el-select
                v-model="softForm.selected_test_item_ids"
                multiple
                filterable
                class="w-full"
                placeholder="选择测试项"
              >
                <el-option
                  v-for="item in testItems"
                  :key="item.id"
                  :label="`${item.name} (${item.category})`"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="测试序列">
              <el-select v-model="softForm.sequence_id" filterable clearable class="w-full" placeholder="选择测试序列">
                <el-option
                  v-for="seq in sequences"
                  :key="seq.id"
                  :label="`${seq.name} (v${seq.version}, ${seq.step_count}步)`"
                  :value="seq.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="选中配置编码">
              <el-input v-model="softForm.selected_code" />
            </el-form-item>
            <el-form-item label="序列快照数据" v-if="softForm.sequence_data && Object.keys(softForm.sequence_data).length">
              <el-input
                v-model="sequenceDataStr"
                type="textarea"
                :rows="4"
                placeholder="序列快照（JSON）"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="softSaving" @click="saveSoftware">保存软件配置</el-button>
            </el-form-item>
          </el-form>
          <div v-else class="text-center text-gray-400 py-8">加载中...</div>
        </el-tab-pane>

        <!-- Tab 4: Scenario Config -->
        <el-tab-pane label="场景参数" name="scenario">
          <el-form v-if="scenarioForm" label-width="100px">
            <el-form-item label="场景数据">
              <el-input
                v-model="scenarioDataStr"
                type="textarea"
                :rows="12"
                placeholder="场景参数 JSON"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="scenarioSaving" @click="saveScenario">保存场景参数</el-button>
              <el-button size="small" class="ml-2" @click="formatScenario">格式化 JSON</el-button>
            </el-form-item>
          </el-form>
          <div v-else class="text-center text-gray-400 py-8">加载中...</div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { stationApi } from '@/api/station'
import { testApi } from '@/api/test'
import { ElMessage, ElMessageBox } from 'element-plus'
import FormDialog from '@/components/FormDialog.vue'

const route = useRoute()
const stationId = Number(route.params.id)
const loading = ref(true)
const stationName = ref('')

const activeTab = ref('equipment')

// ── Equipment Config ──
const equipForm = ref<any>(null)
const equipSaving = ref(false)

async function loadEquipment() {
  try {
    const res = await stationApi.getEquipment(stationId)
    equipForm.value = res.data || {}
  } catch (e: any) {
    ElMessage.error('加载装备参数失败')
  }
}

async function saveEquipment() {
  equipSaving.value = true
  try {
    await stationApi.updateEquipment(stationId, equipForm.value)
    ElMessage.success('装备参数保存成功')
  } finally {
    equipSaving.value = false
  }
}

// ── Hardware Params ──
const hardwareParams = ref<any[]>([])
const hardwareLoading = ref(false)
const hardwareSubmitting = ref(false)
const showBatchReplace = ref(false)
const batchReplaceText = ref('')
const batchSaving = ref(false)

const hardwareDialog = reactive({ visible: false, isEdit: false, editId: 0 })
const hardwareForm = reactive({
  param_name: '', param_value: '', group_name: 'default', sort_order: 0,
})

async function loadHardware() {
  hardwareLoading.value = true
  try {
    const res = await stationApi.listHardware(stationId)
    hardwareParams.value = res.data || []
  } catch (e: any) {
    hardwareParams.value = []
    ElMessage.error('加载硬件参数失败')
  } finally {
    hardwareLoading.value = false
  }
}

function openHardwareDialog(row?: any) {
  if (row) {
    hardwareDialog.isEdit = true
    hardwareDialog.editId = row.id
    Object.assign(hardwareForm, {
      param_name: row.param_name, param_value: row.param_value,
      group_name: row.group_name, sort_order: row.sort_order,
    })
  } else {
    hardwareDialog.isEdit = false
    hardwareDialog.editId = 0
    Object.assign(hardwareForm, { param_name: '', param_value: '', group_name: 'default', sort_order: 0 })
  }
  hardwareDialog.visible = true
}

async function submitHardware() {
  hardwareSubmitting.value = true
  try {
    if (hardwareDialog.isEdit) {
      await stationApi.updateHardware(hardwareDialog.editId, hardwareForm)
      ElMessage.success('硬件参数更新成功')
    } else {
      await stationApi.createHardware(stationId, hardwareForm)
      ElMessage.success('硬件参数创建成功')
    }
    hardwareDialog.visible = false
    await loadHardware()
  } finally {
    hardwareSubmitting.value = false
  }
}

async function handleDeleteHardware(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除参数 "${row.param_name}"？`, '确认')
    await stationApi.deleteHardware(row.id)
    ElMessage.success('硬件参数已删除')
    await loadHardware()
  } catch { /* cancelled */ }
}

async function submitBatchReplace() {
  batchSaving.value = true
  try {
    const lines = batchReplaceText.value.split('\n').filter(Boolean)
    const params = lines.map((line: string) => {
      const [name, ...vals] = line.split('=')
      return { param_name: name.trim(), param_value: vals.join('=').trim(), group_name: 'default', sort_order: 0 }
    })
    await stationApi.batchReplaceHardware(stationId, { params })
    ElMessage.success(`批量替换成功，共 ${params.length} 条`)
    showBatchReplace.value = false
    await loadHardware()
  } finally {
    batchSaving.value = false
  }
}

// ── Software Config ──
const softForm = ref<any>(null)
const softSaving = ref(false)
const testItems = ref<any[]>([])
const sequences = ref<any[]>([])
const sequenceDataStr = ref('')

async function loadSoftware() {
  try {
    const res = await stationApi.getSoftware(stationId)
    softForm.value = res.data || {}
    sequenceDataStr.value = softForm.value.sequence_data
      ? JSON.stringify(softForm.value.sequence_data, null, 2)
      : ''
    const [itemsRes, seqRes] = await Promise.all([
      testApi.listItems(),
      testApi.listSequences(),
    ])
    testItems.value = itemsRes.data || []
    sequences.value = seqRes.data || []
  } catch (e: any) {
    ElMessage.error('加载软件配置失败')
  }
}

async function saveSoftware() {
  softSaving.value = true
  try {
    const data = { ...softForm.value }
    if (sequenceDataStr.value) {
      try { data.sequence_data = JSON.parse(sequenceDataStr.value) }
      catch { data.sequence_data = sequenceDataStr.value }
    }
    await stationApi.updateSoftware(stationId, data)
    ElMessage.success('软件配置保存成功')
  } finally {
    softSaving.value = false
  }
}

// ── Scenario Config ──
const scenarioForm = ref<any>(null)
const scenarioDataStr = ref('')
const scenarioSaving = ref(false)

async function loadScenario() {
  try {
    const res = await stationApi.getScenario(stationId)
    scenarioForm.value = res.data || {}
    scenarioDataStr.value = scenarioForm.value.scenario_data
      ? JSON.stringify(scenarioForm.value.scenario_data, null, 2)
      : '{}'
  } catch (e: any) {
    ElMessage.error('加载场景参数失败')
  }
}

function formatScenario() {
  try {
    scenarioDataStr.value = JSON.stringify(JSON.parse(scenarioDataStr.value), null, 2)
  } catch {
    ElMessage.warning('JSON 格式无效')
  }
}

async function saveScenario() {
  scenarioSaving.value = true
  try {
    let data: any
    try { data = JSON.parse(scenarioDataStr.value) }
    catch { data = scenarioDataStr.value }
    await stationApi.updateScenario(stationId, { scenario_data: data })
    ElMessage.success('场景参数保存成功')
  } finally {
    scenarioSaving.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const stRes = await stationApi.getStation(stationId)
    stationName.value = stRes.data?.name || ''
    await Promise.all([
      loadEquipment(),
      loadHardware(),
      loadSoftware(),
      loadScenario(),
    ])
  } finally {
    loading.value = false
  }
})
</script>
