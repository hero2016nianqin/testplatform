<template>
  <div class="min-w-0">
    <div class="flex items-center gap-2 mb-6">
      <el-icon :size="26" color="var(--el-color-primary)"><Files /></el-icon>
      <div>
        <h1 class="section-title !mb-0 !border-0 !pl-0 text-xl">指标字典库</h1>
        <div class="section-subtitle mt-0.5">全局公共指标池，每条编码维护一套标准硬件执行参数模板</div>
      </div>
    </div>

    <el-card shadow="hover" class="mb-4 app-card-hover">
      <el-form :inline="true" :model="query" @keyup.enter="search">
        <el-form-item label="搜索">
          <el-input v-model="query.keyword" placeholder="指标名称 / 编码" clearable style="width:240px" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="query.category" placeholder="全部分类" clearable style="width:140px">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width:120px">
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search"><el-icon class="mr-1"><Search /></el-icon>搜索</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
        <el-form-item>
          <el-button size="small" @click="openExportDialog()"><el-icon class="mr-1"><Download /></el-icon>导出</el-button>
          <el-button size="small" @click="openRawPreview()"><el-icon class="mr-1"><View /></el-icon>原始数据</el-button>
          <el-button size="small" @click="triggerExcelImport()"><el-icon class="mr-1"><Upload /></el-icon>Excel 导入</el-button>
          <input ref="fileInput" type="file" accept=".xlsx,.xls" class="hidden" @change="handleExcelImport" />
          <el-button type="primary" size="small" @click="openCreateDialog()"><el-icon class="mr-1"><Plus /></el-icon>新增指标</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="hover" class="app-card-hover">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-bold">指标列表</span>
        </div>
      </template>
      <el-table :data="list" stripe v-loading="loading" style="width:100%">
        <el-table-column label="指标编码" width="140">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" class="cursor-pointer font-medium" @click="openEditDialog(row)">{{ row.code }}</el-link>
          </template>
        </el-table-column>
        <el-table-column label="指标名称" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.name }}</template>
        </el-table-column>
        <el-table-column label="领域" width="120">
          <template #default="{ row }">
            <span v-if="row.domain">{{ row.domain }}</span>
            <span v-else class="text-gray-400">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="参数数量" width="90" align="center">
          <template #default="{ row }">{{ (row._params || []).length }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button size="small" @click="showReferences(row)">引用</el-button>
            <el-button size="small" type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" @click="handleToggleStatus(row, row.status === 1 ? 0 : 1)">{{ row.status === 1 ? '停用' : '启用' }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <div class="flex justify-end mt-4" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @change="load"
      />
    </div>

    <!-- Edit Dialog (two tabs: params + script) -->
    <el-dialog v-model="editDialog.visible" :title="editDialog.title" width="960px" top="4vh" :close-on-click-modal="false" destroy-on-close>
      <el-tabs v-model="editTab">
        <el-tab-pane label="基本信息" name="basic">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="指标编码" label-width="90px">
                <el-input v-model="editBasic.code" maxlength="50" disabled />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="指标名称" label-width="90px">
                <el-input v-model="editBasic.name" maxlength="100" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="6">
              <el-form-item label="分类" label-width="90px">
                <el-select v-model="editBasic.category" allow-create filterable clearable class="w-full" placeholder="输入或选择">
                  <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="领域" label-width="90px">
                <el-select v-model="editBasic.domain" allow-create filterable clearable class="w-full" placeholder="输入或选择">
                  <el-option v-for="d in domains" :key="d" :label="d" :value="d" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="单位" label-width="90px">
                <el-input v-model="editBasic.unit" maxlength="20" placeholder="如：dBm、mA" />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="硬件型号" label-width="90px">
                <el-input v-model="editBasic.hardware_model" maxlength="100" placeholder="如：N1914B" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="测试规则" label-width="90px">
            <el-input v-model="editBasic.test_rule" type="textarea" :rows="2" placeholder="文本测试规则说明" />
          </el-form-item>
          <el-form-item label="描述" label-width="90px">
            <el-input v-model="editBasic.description" type="textarea" :rows="2" />
          </el-form-item>
        </el-tab-pane>
        <el-tab-pane label="硬件执行参数" name="params">
          <div class="mb-3 flex items-center gap-2">
            <el-button size="small" type="primary" @click="addParamRow">+ 新增参数</el-button>
            <el-button size="small" @click="clearAllParams" :disabled="!editParams.length">清空全部</el-button>
            <span class="text-xs text-gray-400 ml-2">共 {{ editParams.length }} 条参数</span>
          </div>
          <el-table :data="editParams" stripe size="small" style="width:100%">
            <el-table-column label="参数 Key" width="120">
              <template #default="{ row, $index }">
                <el-input v-model="row.key" size="small" placeholder="英文唯一标识" maxlength="80" :disabled="row._existing" @input="(v: string) => row.key = v.trim()" />
              </template>
            </el-table-column>
            <el-table-column label="参数名称" width="120">
              <template #default="{ row }">
                <el-input v-model="row.name" size="small" placeholder="参数中文名" maxlength="100" />
              </template>
            </el-table-column>
            <el-table-column label="参数值" width="170">
              <template #default="{ row }">
                <el-input
                  v-if="row.format === 'number'"
                  v-model="row.value" size="small" placeholder="请输入数字"
                  @input="onNumberInput(row)"
                  @keydown="onNumberKeydown"
                  :class="row.value && !/^-?\d*\.?\d*$/.test(String(row.value)) ? 'is-error' : ''"
                />
                <el-select v-else-if="row.format === 'boolean'" v-model="row.value" size="small" class="w-full">
                  <el-option label="true" value="true" />
                  <el-option label="false" value="false" />
                </el-select>
                <el-input
                  v-else-if="row.format === 'array'"
                  v-model="row.value" size="small" placeholder="多个值用英文逗号分隔"
                />
                <el-input
                  v-else
                  v-model="row.value" size="small" placeholder="请输入文本值"
                />
              </template>
            </el-table-column>
            <el-table-column label="参数类型" width="110">
              <template #default="{ row }">
                <el-select v-model="row.type" size="small" class="w-full">
                  <el-option label="仪表参数" value="仪表参数" />
                  <el-option label="被测件参数" value="被测件参数" />
                  <el-option label="通用测试参数" value="通用测试参数" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="数据格式" width="110">
              <template #default="{ row }">
                <el-select v-model="row.format" size="small" class="w-full" @change="onFormatChange(row)">
                  <el-option :value="'number'" label="数字" />
                  <el-option :value="'string'" label="字符串" />
                  <el-option :value="'boolean'" label="布尔" />
                  <el-option :value="'array'" label="列表" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="备注" min-width="160">
              <template #default="{ row }">
                <el-input v-model="row.remark" size="small" placeholder="填写参数单位、取值范围、使用说明" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60" fixed="right">
              <template #default="{ row, $index }">
                <el-button size="small" text type="danger" @click="removeParamRow($index)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="转换脚本" name="script">
          <!-- Section 1: Input Params (read-only) -->
          <div class="mb-3 border rounded">
            <div class="flex items-center justify-between bg-gray-50 px-3 py-1.5 border-b text-xs text-gray-500">
              <span class="font-medium">原始入参（indicator_data）</span>
              <div class="flex items-center gap-2">
                <el-button size="small" text @click="scriptInputCollapsed = !scriptInputCollapsed">
                  {{ scriptInputCollapsed ? '展开' : '折叠' }}
                </el-button>
                <el-button size="small" text @click="copyScriptInput">复制入参</el-button>
              </div>
            </div>
            <div v-show="!scriptInputCollapsed" class="p-3 bg-[#f8f9fa] overflow-auto" style="max-height:200px">
              <pre class="text-xs font-mono" style="white-space:pre-wrap" v-html="highlightJson(scriptInputData)"></pre>
            </div>
          </div>

          <!-- Section 2: Script Editor -->
          <div class="flex items-center gap-2 mb-2">
            <el-tag v-if="scriptHasCustom" size="small" type="warning">自定义脚本</el-tag>
            <el-tag v-else size="small" type="info">默认模板</el-tag>
            <el-button size="small" @click="resetScript">重置为默认</el-button>
            <el-button size="small" type="primary" :loading="scriptValidating" @click="validateScriptCode">语法校验</el-button>
          </div>
          <div class="border rounded overflow-hidden" :class="{ 'border-red-500': scriptError }">
            <div class="flex items-center justify-between bg-gray-50 px-3 py-1.5 border-b text-xs text-gray-500">
              <span>indicator_data 为入参，result 为返回值</span>
              <div class="flex items-center gap-2">
                <el-tag v-if="scriptValid === true" size="small" type="success">语法正确</el-tag>
                <el-tag v-else-if="scriptValid === false" size="small" type="danger">语法错误</el-tag>
              </div>
            </div>
            <codemirror
              v-model="scriptSource"
              style="min-height:240px;border:none"
              :extensions="scriptExtensions"
              :disabled="false"
              @change="onScriptChange"
            />
          </div>
          <div v-if="scriptError" class="text-red-500 text-xs mt-1 flex items-center gap-2">
            <el-icon><WarningFilled /></el-icon>
            <span>{{ scriptError }}</span>
          </div>

          <!-- Section 3: Preview Output -->
          <div class="mt-3 border rounded">
            <div class="flex items-center justify-between bg-gray-50 px-3 py-1.5 border-b text-xs text-gray-500">
              <span class="font-medium">转换结果预览</span>
              <div class="flex items-center gap-2">
                <span class="text-gray-400">预览输出与最终 BOM 导出文件内容完全一致</span>
                <el-button size="small" type="primary" :loading="previewLoading" @click="runPreview">一键预览</el-button>
                <el-button size="small" @click="clearPreview">清空预览</el-button>
                <el-button v-if="previewResult" size="small" text @click="copyPreviewOutput">复制结果</el-button>
              </div>
            </div>
            <div v-if="previewLoading" class="p-6 text-center text-gray-400 text-sm">执行中...</div>
            <div v-else-if="previewError" class="p-3 overflow-auto" style="max-height:300px">
              <div class="text-red-500 text-xs font-mono whitespace-pre-wrap">{{ previewError }}</div>
            </div>
            <div v-else-if="previewResult !== null" class="p-3 overflow-auto" style="max-height:300px">
              <pre v-if="typeof previewResult === 'object'" class="text-xs font-mono" style="white-space:pre-wrap" v-html="highlightJson(previewResult)"></pre>
              <pre v-else class="text-xs font-mono" style="white-space:pre-wrap">{{ String(previewResult) }}</pre>
            </div>
            <div v-else class="p-6 text-center text-gray-400 text-sm">点击「一键预览」执行脚本并查看转换结果</div>
          </div>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="editSubmitting" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- Reference Dialog -->
    <el-dialog v-model="refVisible" title="引用详情" width="600px" top="8vh">
      <template v-if="refData">
        <div class="mb-3">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="指标编码">{{ refData.indicator_code }}</el-descriptions-item>
            <el-descriptions-item label="指标名称">{{ refData.indicator_name }}</el-descriptions-item>
          </el-descriptions>
        </div>
        <el-tabs>
          <el-tab-pane :label="`测试项集合 (${refData.total_collections || 0})`" name="collections">
            <template v-if="refData.collections?.length">
              <div v-for="c in refData.collections" :key="c.id" class="mb-3 p-3 rounded" style="background:#f8f9fa">
                <div class="font-bold mb-1">{{ c.name }} ({{ c.code }})</div>
                <div v-for="ti in c.test_items" :key="ti.id" class="text-sm pl-3 text-gray-600">· {{ ti.name }}</div>
              </div>
            </template>
            <el-empty v-else description="未被任何集合引用" :image-size="60" />
          </el-tab-pane>
          <el-tab-pane :label="`BOM配置 (${refData.total_bom_configs || 0})`" name="bom">
            <el-table v-if="refData.bom_configs?.length" :data="refData.bom_configs" stripe size="small" style="width:100%">
              <el-table-column prop="bom_code" label="BOM编码" width="140" />
              <el-table-column prop="bom_name" label="BOM名称" />
            </el-table>
            <el-empty v-else description="未被任何BOM引用" :image-size="60" />
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-dialog>

    <FormDialog
      v-model:visible="formDialog.visible"
      :title="formDialog.isEdit ? '编辑指标' : '新增指标'"
      :form-data="form"
      :rules="rules"
      :submitting="submitting"
      width="720px"
      label-width="90px"
      @submit="submitForm"
    >
      <template #default="{ form: f }">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="指标编码" prop="code">
              <el-input v-model="f.code" maxlength="50" :disabled="formDialog.isEdit" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="指标名称" prop="name">
              <el-input v-model="f.name" maxlength="100" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="分类">
              <el-select v-model="f.category" allow-create filterable clearable class="w-full" placeholder="输入或选择">
                <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="领域">
              <el-select v-model="f.domain" allow-create filterable clearable class="w-full" placeholder="输入或选择">
                <el-option v-for="d in domains" :key="d" :label="d" :value="d" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="单位">
              <el-input v-model="f.unit" maxlength="20" placeholder="如：dBm、mA" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="硬件型号">
              <el-input v-model="f.hardware_model" maxlength="100" placeholder="如：N1914B" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="测试规则">
          <el-input v-model="f.test_rule" type="textarea" :rows="2" placeholder="文本测试规则说明" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="f.description" type="textarea" :rows="2" />
        </el-form-item>
      </template>
    </FormDialog>

    <!-- Raw Data Preview Dialog -->
    <el-dialog v-model="rawVisible" title="原始结构化数据" width="800px" top="5vh">
      <div class="bg-gray-50 rounded p-4 overflow-auto" style="max-height:60vh">
        <pre class="text-xs font-mono" style="white-space:pre-wrap">{{ rawData }}</pre>
      </div>
    </el-dialog>

    <!-- Export Config Dialog -->
    <el-dialog v-model="exportDialog.visible" title="导出配置文件" width="480px" :close-on-click-modal="false">
      <el-form>
        <el-form-item label="导出说明">
          <div class="text-sm text-gray-600">遍历全量启用指标，逐条执行指标自带转换脚本，自动聚合并生成配置文件</div>
        </el-form-item>
        <el-form-item label="输出格式">
          <el-select v-model="exportDialog.format" class="w-full">
            <el-option label="JSON" value="json" />
            <el-option label="INI" value="ini" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exportDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="exporting" @click="submitExport">执行导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, shallowRef } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { WarningFilled } from '@element-plus/icons-vue'
import { metricsApi } from '@/api/metrics'
import FormDialog from '@/components/FormDialog.vue'

// CodeMirror
import { Codemirror } from 'vue-codemirror'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorView } from 'codemirror'

const scriptExtensions = shallowRef([
  python(),
  oneDark,
  EditorView.lineWrapping,
])

// ── Data ──
const list = ref<any[]>([])
const categories = ref<string[]>([])
const domains = ref<string[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const query = reactive({ keyword: '', category: '', status: undefined as number | undefined })

function search() { page.value = 1; load() }
function reset() { query.keyword = ''; query.category = ''; query.status = undefined; page.value = 1; load() }

async function load() {
  loading.value = true
  try {
    const res = await metricsApi.listIndicators({ page: page.value, page_size: pageSize.value, keyword: query.keyword, category: query.category, status: query.status })
    list.value = (res.data?.items || []).map((item: any) => ({ ...item, _params: item.test_params || [] }))
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  const res = await metricsApi.listIndicatorCategories()
  categories.value = res.data || []
}

async function loadDomains() {
  const res = await metricsApi.listIndicatorDomains()
  domains.value = res.data?.domains || []
}

// ── Edit Dialog (three tabs: basic + params + script) ──
const editTab = ref('params')
const editDialog = reactive({ visible: false, item: null as any, title: '' })
const editParams = ref<any[]>([])
const editSubmitting = ref(false)
const editBasic = reactive({
  code: '', name: '', category: '', domain: '', unit: '', hardware_model: '', test_rule: '', description: '',
})

function openEditDialog(row: any) {
  editDialog.item = row
  editDialog.title = `编辑指标 — ${row.code} ${row.name}`
  Object.assign(editBasic, {
    code: row.code || '',
    name: row.name || '',
    category: row.category || '',
    domain: row.domain || '',
    unit: row.unit || '',
    hardware_model: row.hardware_model || '',
    test_rule: row.test_rule || '',
    description: row.description || '',
  })
  editParams.value = (row._params || []).map((p: any) => ({
    key: p.key || '',
    name: p.name || '',
    value: p.value ?? '',
    type: p.type || '通用测试参数',
    format: p.format || 'string',
    remark: p.remark || '',
    _existing: true,
  }))
  // Load script data in background
  loadScriptForEdit(row.id)
  editTab.value = 'params'
  editDialog.visible = true
}

function addParamRow() {
  editParams.value.push({
    key: '', name: '', value: '', type: '通用测试参数', format: 'string', remark: '', _existing: false,
  })
}

function removeParamRow(index: number) {
  editParams.value.splice(index, 1)
}

function clearAllParams() {
  editParams.value = []
}

function onFormatChange(row: any) {
  if (row.format === 'boolean') row.value = 'true'
  else if (row.format === 'number') row.value = row.value?.replace?.(/[^0-9.\-]/g, '') || ''
  else if (row.format === 'array') { /* no-op */ }
}

function onNumberInput(row: any) {
  row.value = row.value?.replace?.(/[^0-9.\-]/g, '') || ''
}

function onNumberKeydown(e: KeyboardEvent) {
  if (e.key === '-' || e.key === '.' || e.key === 'Backspace' || e.key === 'Delete' || e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'Tab' || e.key === 'Enter') return
  if (!/[0-9]/.test(e.key)) e.preventDefault()
}

async function submitEdit() {
  if (!editDialog.item) return
  // Auto-preview check on save
  const previewHasParams = Object.keys(scriptInputData.value).some(k => k !== 'code' && k !== 'name')
  if (scriptSource.value.trim() && previewHasParams) {
    try {
      const check = await metricsApi.previewIndicatorScript(editDialog.item.id, {
        source_code: scriptSource.value,
        input_data: scriptInputData.value,
      })
      if (!check.data?.success) {
        try {
          await ElMessageBox.confirm(
            `脚本执行异常：${check.data?.error || '未知错误'}\n\n是否仍要保存？`,
            '脚本异常确认',
            { confirmButtonText: '强制保存', cancelButtonText: '返回修改', type: 'warning' },
          )
        } catch { return }
      }
    } catch { /* preview network error — allow save anyway */ }
  }
  editSubmitting.value = true
  try {
    const params = editParams.value.map((p: any) => ({
      key: p.key, name: p.name, value: p.value, type: p.type, format: p.format, remark: p.remark,
    }))
    await metricsApi.updateIndicator(editDialog.item.id, {
      test_params: params,
      name: editBasic.name,
      category: editBasic.category,
      domain: editBasic.domain,
      unit: editBasic.unit,
      hardware_model: editBasic.hardware_model || undefined,
      test_rule: editBasic.test_rule,
      description: editBasic.description,
    })
    if (scriptSource.value.trim()) {
      await metricsApi.updateIndicatorScript(editDialog.item.id, { source_code: scriptSource.value })
    }
    ElMessage.success('保存成功')
    editDialog.visible = false
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '保存失败')
  } finally {
    editSubmitting.value = false
  }
}

// ── Script editing (inside edit dialog) ──
const scriptSource = ref('')
const scriptHasCustom = ref(false)
const scriptError = ref('')
const scriptValid = ref<boolean | null>(null)
const scriptValidating = ref(false)
const scriptInputCollapsed = ref(false)
const previewLoading = ref(false)
const previewResult = ref<any>(null)
const previewError = ref('')

const scriptParamNames = computed(() => {
  return editParams.value.map((x: any) => x.name || x.key).filter(Boolean).join(', ') || '无'
})

const scriptInputData = computed(() => {
  const item = editDialog.item
  const data: Record<string, any> = {
    code: item?.code || '',
    name: item?.name || '',
  }
  for (const p of editParams.value) {
    if (!p.key) continue
    const v = p.value
    if (p.format === 'number') data[p.key] = v !== '' && v !== undefined ? Number(v) : ''
    else if (p.format === 'boolean') data[p.key] = v === 'true'
    else if (p.format === 'array') {
      if (v) {
        const items = v.split(',').map((s: string) => s.trim()).filter(Boolean)
        data[p.key] = items.map((s: string) => (isNaN(Number(s)) || s === '') ? s : Number(s))
      } else {
        data[p.key] = []
      }
    }
    else data[p.key] = v ?? ''
  }
  return data
})

async function loadScriptForEdit(indicatorId: number) {
  scriptError.value = ''
  scriptValid.value = null
  previewResult.value = null
  previewError.value = ''
  try {
    const res = await metricsApi.getIndicatorScript(indicatorId)
    const data = res.data
    scriptSource.value = data?.source_code || ''
    scriptHasCustom.value = data?.has_custom || false
  } catch { /* silent */ }
}

function highlightJson(obj: any): string {
  const json = JSON.stringify(obj, null, 2)
  if (!json) return ''
  const escaped = json
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return escaped.replace(
    /("(?:[^"\\]|\\.)*")\s*:|("(?:[^"\\]|\\.)*")|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|(true|false)|(null)/g,
    (_m: string, key: string, str: string, num: string, bool: string, nil: string) => {
      if (key !== undefined) return `<span class="json-key">${key}</span>:`
      if (str !== undefined) return `<span class="json-string">${str}</span>`
      if (num !== undefined) return `<span class="json-number">${num}</span>`
      if (bool !== undefined) return `<span class="json-boolean">${bool}</span>`
      if (nil !== undefined) return `<span class="json-null">${nil}</span>`
      return ''
    }
  )
}

function copyScriptInput() {
  const text = JSON.stringify(scriptInputData.value, null, 2)
  navigator.clipboard.writeText(text).then(() => ElMessage.success('入参已复制')).catch(() => {})
}

function copyPreviewOutput() {
  const text = typeof previewResult.value === 'object' ? JSON.stringify(previewResult.value, null, 2) : String(previewResult.value)
  navigator.clipboard.writeText(text).then(() => ElMessage.success('预览结果已复制')).catch(() => {})
}

function clearPreview() {
  previewResult.value = null
  previewError.value = ''
}

async function runPreview() {
  if (!scriptSource.value.trim()) {
    ElMessage.warning('请先编写脚本')
    return
  }
  previewLoading.value = true
  previewResult.value = null
  previewError.value = ''
  try {
    const res = await metricsApi.previewIndicatorScript(editDialog.item.id, {
      source_code: scriptSource.value,
      input_data: scriptInputData.value,
    })
    const data = res.data
    if (data?.success) {
      previewResult.value = data.result
      if (data.stdout) console.log('[script stdout]', data.stdout)
    } else {
      previewError.value = data?.error || '执行失败'
      if (data?.traceback) previewError.value += '\n\n' + data.traceback
    }
  } catch (e: any) {
    previewError.value = e?.response?.data?.message || '预览请求失败'
  } finally {
    previewLoading.value = false
  }
}

async function validateScriptCode() {
  if (!scriptSource.value.trim()) {
    scriptError.value = '代码为空'
    scriptValid.value = false
    return
  }
  scriptValidating.value = true
  try {
    const res = await metricsApi.validateIndicatorScript(editDialog.item.id, { source_code: scriptSource.value })
    const result = res.data
    if (result?.valid) {
      scriptError.value = ''
      scriptValid.value = true
      ElMessage.success('Python 语法正确')
    } else {
      scriptError.value = result?.message || '语法错误'
      scriptValid.value = false
    }
  } catch {
    scriptError.value = '校验请求失败'
    scriptValid.value = false
  } finally {
    scriptValidating.value = false
  }
}

function onScriptChange(val: string) {
  scriptValid.value = null
  scriptError.value = ''
}

async function saveScript() {
  if (!scriptSource.value.trim()) {
    ElMessage.warning('脚本代码不能为空')
    return
  }
  try {
    await metricsApi.updateIndicatorScript(editDialog.item.id, { source_code: scriptSource.value })
    ElMessage.success('脚本保存成功')
    scriptHasCustom.value = true
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '保存失败')
  }
}

async function resetScript() {
  try {
    await ElMessageBox.confirm('确定重置为系统默认脚本？当前自定义内容将丢失。', '确认重置', { type: 'warning' })
    const res = await metricsApi.resetIndicatorScript(editDialog.item.id)
    scriptSource.value = res.data?.source_code || ''
    scriptHasCustom.value = false
    scriptError.value = ''
    scriptValid.value = null
    ElMessage.success('脚本已重置为默认')
  } catch { /* cancelled */ }
}

// ── Raw Data Preview ──
const rawVisible = ref(false)
const rawData = ref('')

async function openRawPreview() {
  rawVisible.value = true
  const res = await metricsApi.listAllIndicators()
  rawData.value = JSON.stringify(res.data || [], null, 2)
}

// ── Excel Import ──
const fileInput = ref<HTMLInputElement | null>(null)

function triggerExcelImport() {
  fileInput.value?.click()
}

async function handleExcelImport(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  ElMessage.info('正在上传并解析 Excel 文件...')
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await metricsApi.importIndicatorsExcel(formData)
    ElMessage.success(res?.data?.message || '导入成功')
    target.value = ''
    await load()
    await loadCategories()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '导入失败')
  }
}

// ── CRUD (basic info only) ──
const formDialog = reactive({ visible: false, isEdit: false, editId: 0 })
const submitting = ref(false)
const form = reactive({
  code: '', name: '', category: '', domain: '', unit: '', hardware_model: '', description: '', test_rule: '',
})
const rules = {
  code: [{ required: true, message: '请输入指标编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入指标名称', trigger: 'blur' }],
}

function openCreateDialog() {
  formDialog.isEdit = false
  formDialog.editId = 0
  Object.assign(form, { code: '', name: '', category: '', domain: '', unit: '', hardware_model: '', description: '' })
  formDialog.visible = true
}

async function submitForm() {
  submitting.value = true
  try {
    const payload: any = {
      name: form.name, category: form.category, domain: form.domain, unit: form.unit,
      hardware_model: form.hardware_model || undefined, description: form.description,
      params: {},
    }
    if (formDialog.isEdit) {
      await metricsApi.updateIndicator(formDialog.editId, payload)
      ElMessage.success('指标更新成功')
    } else {
      payload.code = form.code
      await metricsApi.createIndicator(payload)
      ElMessage.success('指标创建成功')
    }
    formDialog.visible = false
    await load()
    await loadCategories()
  } finally {
    submitting.value = false
  }
}

// ── References ──
const refVisible = ref(false)
const refData = ref<any>(null)

async function showReferences(row: any) {
  try {
    const res = await metricsApi.getIndicatorReferences(row.id)
    refData.value = { ...res.data, indicator_code: row.code, indicator_name: row.name }
    refVisible.value = true
  } catch { /* handled */ }
}

async function handleToggleStatus(row: any, status: number) {
  const label = status === 1 ? '启用' : '停用'
  if (status === 0) {
    try {
      const res = await metricsApi.getIndicatorReferences(row.id)
      const totalRefs = (res.data?.total_collections || 0) + (res.data?.total_bom_configs || 0)
      if (totalRefs > 0) {
        await ElMessageBox.confirm(
          `该指标当前被 ${res.data.total_collections} 个测试项集合、${res.data.total_bom_configs} 个BOM配置引用。\n停用后，历史绑定数据将保留并标注「已停用」。确定继续？`,
          '停用确认',
          { confirmButtonText: '确定停用', cancelButtonText: '取消', type: 'warning' },
        )
      }
    } catch { return }
  }
  try {
    await ElMessageBox.confirm(`确定${label}指标 "${row.name}"？`, '确认')
    await metricsApi.updateIndicator(row.id, { status })
    ElMessage.success(`指标已${label}`)
    await load()
  } catch { /* cancelled */ }
}

// ── Export Dialog ──
const exportDialog = reactive({ visible: false, format: 'json' })
const exporting = ref(false)

function openExportDialog() {
  exportDialog.format = 'json'
  exportDialog.visible = true
}

async function submitExport() {
  exporting.value = true
  try {
    const res = await metricsApi.exportAllIndicators({ output_format: exportDialog.format })
    const data = res.data
    if (data?.download_url) {
      window.open(data.download_url, '_blank')
    }
    const logMsg = data?.logs?.length
      ? `（成功 ${data.succeeded}/${data.total_indicators}，失败 ${data.failed}）`
      : ''
    ElMessage.success(`导出成功（${data?.execution_time_ms}ms）${logMsg}`)
    exportDialog.visible = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || e?.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  await Promise.all([load(), loadCategories(), loadDomains()])
})
</script>

<style>
.json-key { color: #881391; }
.json-string { color: #0b7500; }
.json-number { color: #994500; }
.json-boolean { color: #0057ae; }
.json-null { color: #808080; }
</style>
