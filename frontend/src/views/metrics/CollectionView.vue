<template>
  <div class="min-w-0">
    <div class="flex items-center gap-2 mb-6">
      <el-icon :size="26" color="var(--el-color-primary)"><Collection /></el-icon>
      <div>
        <h1 class="section-title !mb-0 !border-0 !pl-0 text-xl">测试项集合管理</h1>
        <div class="section-subtitle mt-0.5">测试项集合是BOM与指标之间的中间载体，一套集合可被多个BOM复用</div>
      </div>
    </div>

    <el-card shadow="hover" class="mb-4 app-card-hover">
      <el-form :inline="true" :model="query" @keyup.enter="search">
        <el-form-item label="搜索">
          <el-input v-model="query.keyword" placeholder="集合名称 / 编号" clearable style="width:240px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width:120px">
            <el-option label="启用" :value="1" />
            <el-option label="归档" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search"><el-icon class="mr-1"><Search /></el-icon>搜索</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="hover" class="app-card-hover">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-bold">测试项集合列表</span>
          <el-button type="primary" size="small" @click="openCreateDialog()">
            <el-icon class="mr-1"><Plus /></el-icon>新增集合
          </el-button>
        </div>
      </template>
      <el-table :data="list" stripe v-loading="loading" style="width:100%" @expand-change="handleExpand">
        <el-table-column type="expand" width="40">
          <template #default="{ row }">
            <div class="px-6 py-3">
              <div class="flex items-center gap-3 mb-3">
                <span class="font-bold text-sm">测试项列表</span>
                <el-button size="small" type="primary" @click="openAddItemDialog(row)">
                  <el-icon class="mr-1"><Plus /></el-icon>添加测试项
                </el-button>
              </div>
              <el-table :data="expandedItems[row.id] || []" stripe size="small" style="width:100%">
                <el-table-column prop="name" label="测试项名称" width="160" />
                <el-table-column prop="process_name" label="测试工序" width="120" />
                <el-table-column prop="station" label="测试工位" width="120" />
                <el-table-column prop="test_type" label="测试类型" width="100" />
                <el-table-column label="阻断类型" width="110">
                  <template #default="{ row: item }">
                    <el-tag v-if="item.block_type === 'must_test'" size="small" type="danger">必测不可屏蔽</el-tag>
                    <el-tag v-else-if="item.block_type === 'critical'" size="small" type="warning">关键阻断项</el-tag>
                    <el-tag v-else size="small" type="info">普通项</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="并行" width="60" align="center">
                  <template #default="{ row: item }">
                    <el-icon v-if="item.parallel_enabled" color="#67c23a"><Check /></el-icon>
                    <span v-else class="text-gray-400">-</span>
                  </template>
                </el-table-column>
                <el-table-column prop="timeout_seconds" label="超时(s)" width="70" align="center">
                  <template #default="{ row: item }">
                    <span>{{ item.timeout_seconds ?? '-' }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="sort_order" label="排序" width="60" />
                <el-table-column label="操作" width="140" fixed="right">
                  <template #default="{ row: item }">
                    <el-button size="small" @click="openEditItemDialog(item)">编辑</el-button>
                    <el-button size="small" type="danger" @click="handleDeleteItem(item)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="集合名称" width="180" />
        <el-table-column prop="code" label="编号" width="120" />
        <el-table-column prop="product_type" label="适用产品类型" width="160" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="状态" width="70">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">{{ row.status === 1 ? '启用' : '归档' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="版本" width="60">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" @click="goToVersionHistory(row)">
              {{ row.version }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">{{ row.created_at?.slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button v-if="row.status === 1" size="small" type="danger" @click="handleArchive(row)">归档</el-button>
            <el-button v-else size="small" @click="handleRestore(row)">启用</el-button>
            <el-button size="small" type="primary" @click="goToVersionHistory(row)">查看历史</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @change="load"
        />
      </div>
    </el-card>

    <FormDialog
      v-model:visible="formDialog.visible"
      :title="formDialog.isEdit ? '编辑测试项集合' : '新增测试项集合'"
      :form-data="form"
      :rules="rules"
      :submitting="submitting"
      @submit="submitForm"
    >
      <template #default="{ form: f }">
        <el-form-item label="集合名称" prop="name">
          <el-input v-model="f.name" maxlength="100" />
        </el-form-item>
        <el-form-item label="编号" prop="code">
          <el-input v-model="f.code" maxlength="50" :disabled="formDialog.isEdit" />
        </el-form-item>
        <el-form-item label="适用产品类型">
          <el-input v-model="f.product_type" maxlength="100" placeholder="如：5G模块、物联网模组" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="f.description" type="textarea" :rows="3" />
        </el-form-item>
      </template>
    </FormDialog>

    <FormDialog
      v-model:visible="itemDialog.visible"
      :title="itemDialog.isEdit ? '编辑测试项' : '添加测试项'"
      :form-data="itemForm"
      :rules="itemRules"
      :submitting="itemSubmitting"
      @submit="submitItem"
    >
      <template #default="{ form: f }">
        <el-form-item label="测试项名称" prop="name">
          <el-input v-model="f.name" maxlength="100" />
        </el-form-item>
        <el-form-item label="测试工序">
          <el-input v-model="f.process_name" placeholder="如：组装、测试、包装" />
        </el-form-item>
        <el-form-item label="测试工位">
          <el-input v-model="f.station" placeholder="如：FT1、MP2" />
        </el-form-item>
        <el-form-item label="测试类型">
          <el-select v-model="f.test_type" class="w-full">
            <el-option label="射频" value="射频" />
            <el-option label="功耗" value="功耗" />
            <el-option label="外观" value="外观" />
            <el-option label="功能" value="功能" />
            <el-option label="可靠性" value="可靠性" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="f.sort_order" :min="0" style="width:200px" />
        </el-form-item>
        <el-divider content-position="left" class="!my-2 text-xs">自动化调度配置</el-divider>
        <el-form-item label="微服务地址" prop="service_address">
          <el-autocomplete
            v-model="f.service_address"
            :fetch-suggestions="queryServiceAddressHistory"
            placeholder="请输入 http/https 接口地址，人工测试项留空"
            clearable
            class="w-full"
            @select="(item: any) => f.service_address = item.value"
          />
        </el-form-item>
        <el-form-item label="测试超时时间" prop="timeout_seconds">
          <div class="flex items-center gap-2 w-full">
            <el-input-number v-model="f.timeout_seconds" :min="1" :max="86400" :step="1" style="width:160px" :value-on-clear="null" />
            <span class="text-gray-500 text-sm whitespace-nowrap">秒</span>
            <el-button size="small" @click="f.timeout_seconds = 10" :type="f.timeout_seconds === 10 ? 'primary' : 'default'">10s</el-button>
            <el-button size="small" @click="f.timeout_seconds = 30" :type="f.timeout_seconds === 30 ? 'primary' : 'default'">30s</el-button>
            <el-button size="small" @click="f.timeout_seconds = 60" :type="f.timeout_seconds === 60 ? 'primary' : 'default'">60s</el-button>
            <el-button size="small" @click="f.timeout_seconds = 120" :type="f.timeout_seconds === 120 ? 'primary' : 'default'">120s</el-button>
          </div>
        </el-form-item>
        <el-form-item label="阻断优先级" prop="block_type">
          <el-select v-model="f.block_type" class="w-full">
            <el-option label="必测不可屏蔽" value="must_test" />
            <el-option label="关键阻断项（失败终止整套测试）" value="critical" />
            <el-option label="普通项（失败告警，继续下一项）" value="normal" />
          </el-select>
        </el-form-item>
        <el-form-item label="并行执行" prop="parallel_enabled">
          <el-radio-group v-model="f.parallel_enabled">
            <el-radio :value="true">支持并行</el-radio>
            <el-radio :value="false">串行独占</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="绑定指标">
          <el-select
            v-model="f.indicators"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            :max-collapse-tags="2"
            class="w-full"
            placeholder="可选，测试项可暂不绑定指标"
          >
            <el-option v-for="ind in availableItemIndicators" :key="ind.id" :label="`${ind.name}（${ind.code}）`" :value="ind.id" />
          </el-select>
        </el-form-item>
      </template>
    </FormDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { metricsApi } from '@/api/metrics'
import FormDialog from '@/components/FormDialog.vue'

const router = useRouter()

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const query = reactive({ keyword: '', status: undefined as number | undefined })
function search() { page.value = 1; load() }
function reset() { query.keyword = ''; query.status = undefined; page.value = 1; load() }

function goToVersionHistory(row: any) {
  router.push({
    name: 'MetricsVersions',
    query: { entity_type: 'collection', entity_id: row.id },
  })
}

async function load() {
  loading.value = true
  try {
    const res = await metricsApi.listCollections({ page: page.value, page_size: pageSize.value, keyword: query.keyword, status: query.status })
    list.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

// ── Expand Items ──
const expandedItems = ref<Record<number, any[]>>({})

async function handleExpand(row: any, expandedRows: any[]) {
  const expanded = expandedRows.some((r: any) => r.id === row.id)
  if (expanded) {
    const res = await metricsApi.listCollectionItems(row.id)
    expandedItems.value[row.id] = res.data || []
  } else {
    delete expandedItems.value[row.id]
  }
}

// ── Collection CRUD ──
const formDialog = reactive({ visible: false, isEdit: false, editId: 0 })
const submitting = ref(false)
const form = reactive({ name: '', code: '', product_type: '', description: '' })
const rules = {
  name: [{ required: true, message: '请输入集合名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入集合编号', trigger: 'blur' }],
}

function openCreateDialog() {
  formDialog.isEdit = false
  formDialog.editId = 0
  Object.assign(form, { name: '', code: '', product_type: '', description: '' })
  formDialog.visible = true
}

function openEditDialog(row: any) {
  formDialog.isEdit = true
  formDialog.editId = row.id
  Object.assign(form, { name: row.name, code: row.code, product_type: row.product_type || '', description: row.description || '' })
  formDialog.visible = true
}

async function submitForm() {
  submitting.value = true
  try {
    if (formDialog.isEdit) {
      await metricsApi.updateCollection(formDialog.editId, { name: form.name, product_type: form.product_type, description: form.description })
      ElMessage.success('集合更新成功')
    } else {
      await metricsApi.createCollection({ ...form })
      ElMessage.success('集合创建成功')
    }
    formDialog.visible = false
    await load()
  } finally {
    submitting.value = false
  }
}

async function handleArchive(row: any) {
  try {
    await ElMessageBox.confirm(`确定归档集合 "${row.name}"？`, '确认')
    await metricsApi.deleteCollection(row.id)
    ElMessage.success('集合已归档')
    await load()
  } catch { /* cancelled */ }
}

async function handleRestore(row: any) {
  try {
    await metricsApi.updateCollection(row.id, { status: 1 })
    ElMessage.success('集合已启用')
    await load()
  } catch { /* handled */ }
}

// ── Item CRUD ──
const itemDialog = reactive({ visible: false, isEdit: false, editId: 0, collectionId: 0 })
const itemSubmitting = ref(false)
const itemForm = reactive({ name: '', process_name: '', station: '', test_type: '', sort_order: 0, service_address: '', timeout_seconds: 30, block_type: 'normal', parallel_enabled: false, indicators: [] as number[] })
const itemRules = {
  name: [{ required: true, message: '请输入测试项名称', trigger: 'blur' }],
  service_address: [{
    validator: (_rule: any, value: string, callback: Function) => {
      if (value && !/^https?:\/\//.test(value)) {
        callback(new Error('微服务地址必须以 http:// 或 https:// 开头'))
      } else {
        callback()
      }
    }, trigger: 'blur',
  }],
}

// ── Indicators selectable when adding a test item ──
const availableItemIndicators = ref<any[]>([])

async function loadAvailableItemIndicators() {
  const res = await metricsApi.listAllIndicators()
  availableItemIndicators.value = res.data || []
}

const STORAGE_KEY = 'service_address_history'
const serviceAddressHistory = ref<{ value: string }[]>([])

function loadServiceAddressHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    serviceAddressHistory.value = raw ? JSON.parse(raw).slice(0, 10) : []
  } catch { serviceAddressHistory.value = [] }
}

function saveServiceAddressHistory(address: string) {
  if (!address) return
  loadServiceAddressHistory()
  const exists = serviceAddressHistory.value.some((item) => item.value === address)
  if (!exists) {
    serviceAddressHistory.value.unshift({ value: address })
    if (serviceAddressHistory.value.length > 10) serviceAddressHistory.value.length = 10
    localStorage.setItem(STORAGE_KEY, JSON.stringify(serviceAddressHistory.value))
  }
}

function queryServiceAddressHistory(queryString: string, cb: (results: { value: string }[]) => void) {
  loadServiceAddressHistory()
  const results = queryString
    ? serviceAddressHistory.value.filter((item) => item.value.toLowerCase().includes(queryString.toLowerCase()))
    : serviceAddressHistory.value
  cb(results)
}

function openAddItemDialog(row: any) {
  itemDialog.collectionId = row.id
  itemDialog.isEdit = false
  itemDialog.editId = 0
  Object.assign(itemForm, { name: '', process_name: '', station: '', test_type: '', sort_order: 0, service_address: '', timeout_seconds: 30, block_type: 'normal', parallel_enabled: false, indicators: [] })
  itemDialog.visible = true
  loadAvailableItemIndicators()
}

// Currently bound indicators while editing (for diff on save)
const itemEditBound = ref<any[]>([])

async function openEditItemDialog(row: any) {
  itemDialog.collectionId = row.collection_id
  itemDialog.isEdit = true
  itemDialog.editId = row.id
  Object.assign(itemForm, {
    name: row.name,
    process_name: row.process_name || '',
    station: row.station || '',
    test_type: row.test_type || '',
    sort_order: row.sort_order || 0,
    service_address: row.service_address || '',
    timeout_seconds: row.timeout_seconds ?? 30,
    block_type: row.block_type || 'normal',
    parallel_enabled: !!row.parallel_enabled,
    indicators: [],
  })
  const indRes = await metricsApi.listItemIndicators(row.id)
  const bound = indRes.data || []
  itemEditBound.value = bound
  itemForm.indicators = bound.map((i: any) => i.indicator_id)
  await loadAvailableItemIndicators()
  itemDialog.visible = true
}

async function submitItem() {
  itemSubmitting.value = true
  try {
    const selectedIds = itemForm.indicators || []
    let newItemId = 0
    if (itemDialog.isEdit) {
      await metricsApi.updateCollectionItem(itemDialog.editId, { ...itemForm })
      // Sync indicators: remove unselected, add newly selected
      const boundList = itemEditBound.value || []
      const boundIds = boundList.map((i: any) => i.indicator_id)
      const toRemove = boundList.filter((i: any) => !selectedIds.includes(i.indicator_id))
      const toAdd = selectedIds.filter((id: number) => !boundIds.includes(id))
      for (const b of toRemove) {
        await metricsApi.deleteItemIndicator(b.id)
      }
      if (toAdd.length) {
        const indicators = availableItemIndicators.value
          .filter((ind: any) => toAdd.includes(ind.id))
          .map((ind: any) => ({
            indicator_id: ind.id,
            unit: ind.unit,
            judgment_rule: '合格',
          }))
        if (indicators.length) await metricsApi.batchAddItemIndicators(itemDialog.editId, { indicators })
      }
      if (toRemove.length || toAdd.length) {
        ElMessage.success('测试项及指标绑定已更新')
      } else {
        ElMessage.success('测试项更新成功')
      }
    } else {
      const res = await metricsApi.createCollectionItem(itemDialog.collectionId, { ...itemForm })
      ElMessage.success('测试项添加成功')
      newItemId = res.data?.id || 0
      if (newItemId && selectedIds.length) {
        const indicators = availableItemIndicators.value
          .filter((ind: any) => selectedIds.includes(ind.id))
          .map((ind: any) => ({
            indicator_id: ind.id,
            unit: ind.unit,
            judgment_rule: '合格',
          }))
        if (indicators.length) {
          await metricsApi.batchAddItemIndicators(newItemId, { indicators })
          ElMessage.success(`并已绑定 ${indicators.length} 个指标`)
        }
      }
    }
    saveServiceAddressHistory(itemForm.service_address)
    itemDialog.visible = false
    const res = await metricsApi.listCollectionItems(itemDialog.collectionId)
    expandedItems.value[itemDialog.collectionId] = res.data || []
  } finally {
    itemSubmitting.value = false
  }
}

async function handleDeleteItem(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除测试项 "${row.name}"？`, '确认')
    await metricsApi.deleteCollectionItem(row.id)
    ElMessage.success('测试项已删除')
    const res = await metricsApi.listCollectionItems(row.collection_id)
    expandedItems.value[row.collection_id] = res.data || []
  } catch { /* cancelled */ }
}

onMounted(load)
</script>
