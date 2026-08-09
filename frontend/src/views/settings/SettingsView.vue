<template>
  <div>
    <div class="flex items-center gap-2 mb-6">
      <el-icon :size="26" color="var(--el-color-primary)"><Setting /></el-icon>
      <div>
        <h1 class="section-title !mb-0 !border-0 !pl-0 text-xl">全局配置</h1>
        <div class="section-subtitle mt-0.5">测试项 / 配置定义 / 序列管理</div>
      </div>
    </div>

    <el-card shadow="hover" class="app-card-hover">
      <el-tabs v-model="activeTab">
        <!-- Tab 1: Test Items -->
        <el-tab-pane label="测试项" name="items">
          <div class="mb-3">
            <el-button type="primary" size="small" @click="openItemDialog()"><el-icon class="mr-1"><Plus /></el-icon>新建测试项</el-button>
          </div>
          <el-table :data="testItems" v-loading="itemsLoading" stripe size="small" style="width: 100%">
            <el-table-column prop="name" label="名称" min-width="150" />
            <el-table-column prop="category" label="分类" width="100" />
            <el-table-column prop="expected_value" label="期望值" width="90" />
            <el-table-column prop="min_value" label="下限" width="80" />
            <el-table-column prop="max_value" label="上限" width="80" />
            <el-table-column prop="unit" label="单位" width="70" />
            <el-table-column prop="sort_order" label="排序" width="60" />
            <el-table-column label="启用" width="60">
              <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '是' : '否' }}</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openItemDialog(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="handleDeleteItem(row)">删除</el-button>
              </template>
            </el-table-column>
            <template #empty>
              <div class="flex flex-col items-center py-8 text-gray-400">
                <el-icon :size="34" color="#c0c8d4"><Files /></el-icon>
                <div class="mt-2 text-sm">暂无数据</div>
              </div>
            </template>
          </el-table>
        </el-tab-pane>

        <!-- Tab 2: Import -->
        <el-tab-pane label="导入" name="import">
          <el-upload
            drag
            :auto-upload="false"
            :limit="1"
            @change="handleImportFile"
          >
            <el-icon class="text-4xl"><UploadFilled /></el-icon>
            <div class="text-sm">拖拽 CSV/Excel 文件到此处，或点击上传</div>
            <template #tip><span class="text-xs text-gray-400">支持 .csv, .xlsx 格式的测试项导入</span></template>
          </el-upload>
          <div class="mt-3" v-if="importFile">
            <el-button type="primary" :loading="importing" @click="submitImport">开始导入</el-button>
            <span class="ml-2 text-sm text-gray-500">{{ importFile?.name }}</span>
          </div>
        </el-tab-pane>

        <!-- Tab 3: Export -->
        <el-tab-pane label="导出" name="export">
          <p class="text-gray-500 mb-4">选择要导出的配置类型：</p>
          <el-checkbox-group v-model="exportTypes">
            <el-checkbox label="test_items" value="test_items">测试项</el-checkbox>
            <el-checkbox label="test_sequences" value="test_sequences">测试序列</el-checkbox>
            <el-checkbox label="definitions" value="definitions">装备定义</el-checkbox>
            <el-checkbox label="hardware_params" value="hardware_params">硬件参数模板</el-checkbox>
          </el-checkbox-group>
          <el-button type="primary" class="mt-3" @click="handleExport">导出选中配置</el-button>
        </el-tab-pane>

        <!-- Tab 4: Config Schemes -->
        <el-tab-pane label="配置方案" name="configs">
          <div class="text-center text-gray-400 py-8">
            配置方案管理 — 管理不同产品类型的配置模板集合
          </div>
        </el-tab-pane>

        <!-- Tab 5: Equipment Definitions -->
        <el-tab-pane label="装备定义" name="definitions">
          <div class="mb-3">
            <el-button type="primary" size="small" @click="openDefDialog()"><el-icon class="mr-1"><Plus /></el-icon>新建定义</el-button>
          </div>
          <el-table :data="definitions" v-loading="defLoading" stripe size="small" style="width: 100%">
            <el-table-column prop="name" label="名称" min-width="150" />
            <el-table-column prop="code" label="编码" width="100" />
            <el-table-column prop="current_version" label="版本" width="80" />
            <el-table-column label="布局" min-width="140">
              <template #default="{ row }">
                <span class="text-xs text-gray-500">{{ layoutSummary(row.layout_config) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="openDefDialog(row)">编辑</el-button>
              </template>
            </el-table-column>
            <template #empty>
              <div class="flex flex-col items-center py-8 text-gray-400">
                <el-icon :size="34" color="#c0c8d4"><Files /></el-icon>
                <div class="mt-2 text-sm">暂无数据</div>
              </div>
            </template>
          </el-table>
        </el-tab-pane>

        <!-- Tab 6: Factory/Line (codeless) -->
        <el-tab-pane label="厂区线体" name="factories">
          <div class="text-center text-gray-400 py-8">
            厂区线体管理请前往 <router-link to="/equipment" class="text-blue-500">线体装备</router-link> 页面
          </div>
        </el-tab-pane>

        <!-- Tab 7: Sequences -->
        <el-tab-pane label="测试序列" name="sequences">
          <div class="mb-3">
            <el-button type="primary" size="small" @click="openSeqDialog()"><el-icon class="mr-1"><Plus /></el-icon>新建序列</el-button>
          </div>
          <el-table :data="sequences" v-loading="seqLoading" stripe size="small" style="width: 100%">
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column prop="version" label="版本" width="80" />
            <el-table-column prop="step_count" label="步骤数" width="80" />
            <el-table-column prop="is_active" label="启用" width="60">
              <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '是' : '否' }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="created_by" label="创建人" width="100" />
            <el-table-column label="操作" width="260" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="viewSeqSteps(row)">步骤</el-button>
                <el-button size="small" @click="openSeqDialog(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="handleDeleteSeq(row)">删除</el-button>
              </template>
            </el-table-column>
            <template #empty>
              <div class="flex flex-col items-center py-8 text-gray-400">
                <el-icon :size="34" color="#c0c8d4"><Files /></el-icon>
                <div class="mt-2 text-sm">暂无数据</div>
              </div>
            </template>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- Test Item Dialog -->
    <FormDialog
      v-model:visible="itemDialog.visible"
      :title="itemDialog.isEdit ? '编辑测试项' : '新建测试项'"
      :form-data="itemForm"
      :rules="{ name: [{ required: true, message: '请输入名称', trigger: 'blur' }] }"
      :submitting="itemSubmitting"
      @submit="submitItem"
    >
      <template #default="{ form }">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="期望值" prop="expected_value">
              <el-input-number v-model="form.expected_value" :min="0" :step="0.1" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="下限" prop="min_value">
              <el-input-number v-model="form.min_value" :min="0" :step="0.1" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="上限" prop="max_value">
              <el-input-number v-model="form.max_value" :min="0" :step="0.1" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="单位" prop="unit">
              <el-input v-model="form.unit" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="分类" prop="category">
              <el-select v-model="form.category" class="w-full">
                <el-option label="通用" value="general" />
                <el-option label="电压" value="voltage" />
                <el-option label="电流" value="current" />
                <el-option label="频率" value="frequency" />
                <el-option label="功率" value="power" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="排序" prop="sort_order">
              <el-input-number v-model="form.sort_order" :min="0" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </template>
    </FormDialog>

    <!-- Definition Dialog -->
    <el-dialog
      v-model="defDialog.visible"
      :title="defDialog.isEdit ? '编辑装备定义' : '新建装备定义'"
      width="860px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form :model="defForm" label-width="100px" v-loading="defSubmitting">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="名称" prop="name" :rules="[{ required: true, message: '请输入名称', trigger: 'blur' }]">
              <el-input v-model="defForm.name" placeholder="如: 老化测试机" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="编码" prop="code">
              <el-input v-model="defForm.code" placeholder="如: AGING-01" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="版本" prop="current_version">
              <el-input v-model="defForm.current_version" placeholder="1.0.0" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述" prop="description">
          <el-input v-model="defForm.description" type="textarea" :rows="2" placeholder="装备定义描述" />
        </el-form-item>

        <el-divider>机柜布局 <span class="text-gray-400 text-xs font-normal ml-2">添加机柜并在机柜内配置机框和槽位数量</span></el-divider>

        <!-- Visual Layout Builder -->
        <div v-if="layoutCabinets.length === 0" class="layout-empty">
          <el-icon :size="32" color="#c0c8d4"><FolderOpened /></el-icon>
          <p class="text-gray-400 text-sm mt-2">暂无机柜，点击下方按钮添加</p>
        </div>

        <div v-for="(cab, ci) in layoutCabinets" :key="ci" class="layout-cabinet">
          <div class="cabinet-head">
            <el-icon :size="18" color="#409EFF"><Cpu /></el-icon>
            <el-input v-model="cab.name" class="cabinet-name-input" size="small" placeholder="机柜名称" />
            <el-tag size="small" type="info" class="ml-1">{{ cab.chassis.length }} 个机框</el-tag>
            <div class="cabinet-actions">
              <el-button size="small" @click="addChassis(ci)">
                <el-icon><Plus /></el-icon> 机框
              </el-button>
              <el-button size="small" type="danger" plain @click="removeCabinet(ci)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>

          <div v-if="cab.chassis.length === 0" class="chassis-empty">
            暂无机框，点击上方「机框」按钮添加
          </div>

          <div v-for="(ch, si) in cab.chassis" :key="si" class="layout-chassis">
            <div class="chassis-head">
              <span class="chassis-icon">📦</span>
              <el-input v-model="ch.name" class="chassis-name-input" size="small" placeholder="机框名称" />
              <span class="slot-label ml-auto">槽位:</span>
              <el-input-number v-model="ch.slot_count" :min="1" :max="48" size="small" class="slot-count-input" controls-position="right" />
              <el-button size="small" circle text @click="removeChassis(ci, si)">
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
            <!-- Slot Visual Preview -->
            <div class="slot-preview">
              <div
                v-for="s in Math.min(ch.slot_count, 24)"
                :key="s"
                class="slot-dot"
                :title="'槽位 ' + s"
              >
                <span class="slot-dot-label">S{{ s }}</span>
              </div>
              <div v-if="ch.slot_count > 24" class="slot-dot slot-dot-more" title="更多槽位">
                <span class="slot-dot-label">+{{ ch.slot_count - 24 }}</span>
              </div>
            </div>
          </div>
        </div>

        <el-button size="small" class="mt-2" @click="addCabinet">
          <el-icon><Plus /></el-icon> 添加机柜
        </el-button>

        <div class="layout-summary" v-if="layoutCabinets.length > 0">
          共 <strong>{{ layoutCabinets.length }}</strong> 个机柜，
          <strong>{{ totalChassis }}</strong> 个机框，
          <strong>{{ totalSlots }}</strong> 个槽位
        </div>
      </el-form>

      <template #footer>
        <el-button @click="defDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="defSubmitting" @click="submitDef">保存</el-button>
      </template>
    </el-dialog>

    <!-- Sequence Dialog -->
    <FormDialog
      v-model:visible="seqDialog.visible"
      :title="seqDialog.isEdit ? '编辑测试序列' : '新建测试序列'"
      :form-data="seqForm"
      :rules="{ name: [{ required: true, message: '请输入名称', trigger: 'blur' }] }"
      :submitting="seqSubmitting"
      @submit="submitSeq"
      width="700px"
    >
      <template #default="{ form }">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="版本" prop="version">
              <el-input v-model="form.version" placeholder="1.0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="创建人" prop="created_by">
              <el-input v-model="form.created_by" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>

        <el-divider>步骤</el-divider>
        <div v-for="(step, i) in seqSteps" :key="i" class="flex items-center gap-2 mb-2">
          <span class="text-gray-400 text-sm w-6">{{ i + 1 }}</span>
          <el-select v-model="step.template_id" filterable placeholder="选择模板" style="width: 250px">
            <el-option v-for="tpl in templates" :key="tpl.id" :label="tpl.name" :value="tpl.id" />
          </el-select>
          <el-input-number v-model="step.timeout_seconds" :min="1" :max="3600" size="small" />
          <el-button type="danger" size="small" @click="seqSteps.splice(i, 1)">移除</el-button>
        </div>
        <el-button size="small" @click="addSeqStep">+ 添加步骤</el-button>
      </template>
    </FormDialog>

    <!-- Sequence Steps View Dialog -->
    <el-dialog v-model="stepsVisible" title="序列步骤" width="600px">
      <el-table :data="viewSteps" stripe size="small">
        <el-table-column type="index" label="步骤" width="60" />
        <el-table-column prop="template_name" label="模板名称" />
        <el-table-column prop="template_is_critical" label="关键项" width="80">
          <template #default="{ row }"><el-tag :type="row.template_is_critical ? 'danger' : 'info'" size="small">{{ row.template_is_critical ? '是' : '否' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="timeout_seconds" label="超时(s)" width="80" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { testApi } from '@/api/test'
import { stationApi } from '@/api/station'
import { ElMessage, ElMessageBox } from 'element-plus'
import FormDialog from '@/components/FormDialog.vue'

const activeTab = ref('items')

// ── Test Items ──
const testItems = ref<any[]>([])
const itemsLoading = ref(false)
const itemSubmitting = ref(false)
const itemDialog = reactive({ visible: false, isEdit: false, editId: 0 })
const itemForm = reactive({
  name: '', description: '', expected_value: 0,
  min_value: 0, max_value: 0, unit: '',
  category: 'general', is_active: true, sort_order: 0,
})

async function fetchItems() {
  itemsLoading.value = true
  try {
    const res = await testApi.listItems()
    testItems.value = res.data || []
  } catch (e: any) {
    testItems.value = []
    ElMessage.error('加载测试项失败')
  } finally { itemsLoading.value = false }
}

function openItemDialog(row?: any) {
  if (row) {
    itemDialog.isEdit = true; itemDialog.editId = row.id
    Object.assign(itemForm, row)
  } else {
    itemDialog.isEdit = false; itemDialog.editId = 0
    Object.assign(itemForm, { name: '', description: '', expected_value: 0, min_value: 0, max_value: 0, unit: '', category: 'general', is_active: true, sort_order: 0 })
  }
  itemDialog.visible = true
}

async function submitItem() {
  itemSubmitting.value = true
  try {
    if (itemDialog.isEdit) {
      await testApi.updateItem(itemDialog.editId, itemForm)
      ElMessage.success('测试项更新成功')
    } else {
      await testApi.createItem(itemForm)
      ElMessage.success('测试项创建成功')
    }
    itemDialog.visible = false
    await fetchItems()
  } finally { itemSubmitting.value = false }
}

async function handleDeleteItem(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除测试项 "${row.name}"？`, '确认')
    await testApi.deleteItem(row.id)
    ElMessage.success('测试项已删除')
    await fetchItems()
  } catch { /* cancelled */ }
}

// ── Import ──
const importFile = ref<any>(null)
const importing = ref(false)

function handleImportFile(uploadFile: any) {
  importFile.value = uploadFile.raw || uploadFile
}

async function submitImport() {
  importing.value = true
  try {
    ElMessage.success('导入成功（模拟）')
    importFile.value = null
  } finally { importing.value = false }
}

// ── Export ──
const exportTypes = ref<string[]>([])

function handleExport() {
  if (exportTypes.value.length === 0) { ElMessage.warning('请选择导出类型'); return }
  ElMessage.success(`已导出: ${exportTypes.value.join(', ')}`)
}

// ── Definitions ──
const definitions = ref<any[]>([])
const defLoading = ref(false)
const defSubmitting = ref(false)
const defDialog = reactive({ visible: false, isEdit: false, editId: 0 })
const defForm = reactive({ name: '', code: '', description: '', current_version: '1.0.0', layout_config: {} })

interface ChassisDef { name: string; slot_count: number }
interface CabinetDef { name: string; chassis: ChassisDef[] }
const layoutCabinets = ref<CabinetDef[]>([])

const totalChassis = computed(() =>
  layoutCabinets.value.reduce((s, c) => s + c.chassis.length, 0)
)
const totalSlots = computed(() =>
  layoutCabinets.value.reduce((s, c) =>
    s + c.chassis.reduce((cs, ch) => cs + (ch.slot_count || 0), 0), 0)
)

function addCabinet() {
  layoutCabinets.value.push({ name: `机柜 ${layoutCabinets.value.length + 1}`, chassis: [] })
}

function addChassis(ci: number) {
  const cab = layoutCabinets.value[ci]
  cab.chassis.push({ name: `机框 ${cab.chassis.length + 1}`, slot_count: 4 })
}

function removeCabinet(ci: number) {
  layoutCabinets.value.splice(ci, 1)
}

function removeChassis(ci: number, si: number) {
  layoutCabinets.value[ci].chassis.splice(si, 1)
}

function defLayoutToJSON(): any {
  return { cabinets: layoutCabinets.value.map(c => ({ ...c, chassis: c.chassis.map(ch => ({ ...ch })) })) }
}

function layoutSummary(layout: any): string {
  if (!layout?.cabinets?.length) return '—'
  const cabs = layout.cabinets.length
  const chs = layout.cabinets.reduce((s: number, c: any) => s + (c.chassis?.length || 0), 0)
  const slts = layout.cabinets.reduce((s: number, c: any) =>
    s + (c.chassis?.reduce((cs: number, ch: any) => cs + (ch.slot_count || 0), 0) || 0), 0)
  return `${cabs}柜/${chs}框/${slts}槽`
}

function loadLayoutFromJSON(layout: any) {
  layoutCabinets.value = []
  if (!layout || !layout.cabinets) return
  for (const cab of layout.cabinets) {
    const entry: CabinetDef = { name: cab.name || '机柜', chassis: [] }
    if (cab.chassis) {
      for (const ch of cab.chassis) {
        entry.chassis.push({ name: ch.name || '机框', slot_count: ch.slot_count || 4 })
      }
    }
    layoutCabinets.value.push(entry)
  }
}

async function fetchDefinitions() {
  defLoading.value = true
  try {
    const res = await stationApi.listDefinitions()
    definitions.value = res.data || []
  } catch (e: any) {
    definitions.value = []
    ElMessage.error('加载装备定义失败')
  } finally { defLoading.value = false }
}

function openDefDialog(row?: any) {
  if (row) {
    defDialog.isEdit = true; defDialog.editId = row.id
    Object.assign(defForm, { name: row.name, code: row.code || '', description: row.description, current_version: row.current_version })
    loadLayoutFromJSON(row.layout_config)
  } else {
    defDialog.isEdit = false; defDialog.editId = 0
    Object.assign(defForm, { name: '', code: '', description: '', current_version: '1.0.0' })
    layoutCabinets.value = []
  }
  defDialog.visible = true
}

async function submitDef() {
  if (!defForm.name.trim()) { ElMessage.warning('请输入名称'); return }
  defSubmitting.value = true
  try {
    const data = { ...defForm }
    data.layout_config = defLayoutToJSON()
    if (defDialog.isEdit) {
      await stationApi.updateDefinition(defDialog.editId, data)
      ElMessage.success('装备定义更新成功')
    } else {
      await stationApi.createDefinition(data)
      ElMessage.success('装备定义创建成功')
    }
    defDialog.visible = false
    await fetchDefinitions()
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    defSubmitting.value = false
  }
}

// ── Sequences ──
const sequences = ref<any[]>([])
const templates = ref<any[]>([])
const seqLoading = ref(false)
const seqSubmitting = ref(false)
const seqDialog = reactive({ visible: false, isEdit: false, editId: 0 })
const seqForm = reactive({ name: '', description: '', version: '1.0', created_by: '' })
const seqSteps = reactive<any[]>([])

async function fetchSequences() {
  seqLoading.value = true
  try {
    const [seqRes, tplRes] = await Promise.all([
      testApi.listSequences(),
      testApi.listTemplates(),
    ])
    sequences.value = seqRes.data || []
    templates.value = tplRes.data || []
  } catch (e: any) {
    sequences.value = []; templates.value = []
    ElMessage.error('加载序列失败')
  } finally { seqLoading.value = false }
}

function addSeqStep() {
  seqSteps.push({ template_id: null, step_order: seqSteps.length + 1, timeout_seconds: 60 })
}

function openSeqDialog(row?: any) {
  if (row) {
    seqDialog.isEdit = true; seqDialog.editId = row.id
    Object.assign(seqForm, { name: row.name, description: row.description, version: row.version, created_by: row.created_by })
    seqSteps.length = 0
  } else {
    seqDialog.isEdit = false; seqDialog.editId = 0
    Object.assign(seqForm, { name: '', description: '', version: '1.0', created_by: '' })
    seqSteps.length = 0
    addSeqStep()
  }
  seqDialog.visible = true
}

async function submitSeq() {
  if (seqSteps.length === 0) { ElMessage.warning('请至少添加一个步骤'); return }
  seqSubmitting.value = true
  try {
    const data = {
      ...seqForm,
      steps: seqSteps.map((s, i) => ({ template_id: s.template_id, step_order: i + 1, timeout_seconds: s.timeout_seconds })),
    }
    if (seqDialog.isEdit) {
      await testApi.updateSequence(seqDialog.editId, data)
      ElMessage.success('测试序列更新成功')
    } else {
      await testApi.createSequence(data)
      ElMessage.success('测试序列创建成功')
    }
    seqDialog.visible = false
    await fetchSequences()
  } finally { seqSubmitting.value = false }
}

async function handleDeleteSeq(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除序列 "${row.name}"？`, '确认')
    await testApi.deleteSequence(row.id)
    ElMessage.success('序列已删除')
    await fetchSequences()
  } catch { /* cancelled */ }
}

const stepsVisible = ref(false)
const viewSteps = ref<any[]>([])

async function viewSeqSteps(row: any) {
  try {
    const res = await testApi.getSequence(row.id)
    viewSteps.value = res.data?.steps || []
    stepsVisible.value = true
  } catch { /* ignore */ }
}

onMounted(async () => {
  await Promise.all([
    fetchItems(),
    fetchDefinitions(),
    fetchSequences(),
  ])
})
</script>

<style scoped>
.layout-empty {
  text-align: center; padding: 24px 0;
  border: 2px dashed #d9d9d9; border-radius: 8px;
  margin-bottom: 12px;
}
.layout-cabinet {
  border: 1px solid #e4e7ed; border-radius: 8px;
  margin-bottom: 12px; overflow: hidden;
}
.cabinet-head {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px;
  background: linear-gradient(135deg, #f0f5ff 0%, #e8f0fe 100%);
  border-bottom: 1px solid #e4e7ed;
}
.cabinet-name-input { width: 160px; }
.cabinet-actions { margin-left: auto; display: flex; gap: 4px; }
.chassis-empty {
  padding: 16px; text-align: center; color: #999; font-size: 0.85rem;
}
.layout-chassis {
  margin: 8px 12px;
  border: 1px solid #ebeef5; border-radius: 6px;
  background: #fafafa;
}
.chassis-head {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 10px;
  border-bottom: 1px solid #ebeef5;
}
.chassis-icon { font-size: 1rem; }
.chassis-name-input { width: 140px; }
.slot-label { font-size: 0.8rem; color: #909399; margin-right: 4px; }
.slot-count-input { width: 100px; }
.slot-preview {
  display: flex; flex-wrap: wrap; gap: 6px;
  padding: 8px 10px;
}
.slot-dot {
  width: 36px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  background: #ecf5ff; border: 1px solid #d9ecff;
  border-radius: 4px; font-size: 0.7rem; color: #409EFF;
  font-weight: 600;
}
.slot-dot-more {
  background: #f5f7fa; border-color: #e4e7ed; color: #909399;
}
.slot-dot-label { line-height: 1; }
.layout-summary {
  text-align: right; font-size: 0.8rem; color: #909399;
  margin-top: 8px; padding-top: 8px;
  border-top: 1px solid #ebeef5;
}
</style>
