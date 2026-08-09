<template>
  <div class="min-w-0">
    <div class="flex items-center gap-2 mb-6">
      <el-icon :size="26" color="var(--el-color-primary)"><Odometer /></el-icon>
      <div>
        <h1 class="section-title !mb-0 !border-0 !pl-0 text-xl">BOM 指标配置</h1>
        <div class="section-subtitle mt-0.5">BOM ↔ 测试项集合 ↔ 指标关联配置</div>
      </div>
    </div>

    <!-- Filter -->
    <el-card shadow="hover" class="mb-4 app-card-hover">
      <el-form :inline="true" :model="query" @keyup.enter="search">
        <el-form-item label="搜索">
          <el-input v-model="query.keyword" placeholder="BOM编码 / 名称" clearable style="width:240px" />
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
      </el-form>
    </el-card>

    <!-- Table -->
    <el-card shadow="hover" class="app-card-hover">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-bold">BOM绑定列表</span>
          <div class="flex items-center gap-2">
            <el-button type="primary" size="small" @click="openBindDialog()">
              <el-icon class="mr-1"><Plus /></el-icon>新增绑定
            </el-button>
          </div>
        </div>
      </template>
      <el-table :data="bomList" stripe v-loading="loading" style="width:100%">
        <el-table-column label="BOM编码" width="160">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" style="cursor:pointer" @click="goToDetail(row)">
              {{ row.bom_code }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="bom_name" label="BOM名称" width="180" show-overflow-tooltip />
        <el-table-column label="绑定集合" width="160">
          <template #default="{ row }">
            <span v-if="collectionMap[row.collection_id]">{{ collectionMap[row.collection_id] }}</span>
            <el-tag v-else size="small" type="warning">{{ row.collection_id }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="集合版本" width="160">
          <template #default="{ row }">
            <el-tooltip placement="top" :content="`版本 ${row.collection_version}${row.is_latest ? '（最新版本）' : ''}`">
              <span class="inline-flex items-center gap-1">
                <span>v{{ row.collection_version }}</span>
                <el-tag v-if="row.is_latest" size="small" type="success" class="ml-1">最新版本</el-tag>
                <el-button v-else-if="!row.archived && row.review_status !== 'approved'" size="small" type="primary" link @click="upgradeToLatest(row)">升级至最新版</el-button>
                <el-tag v-else size="small" type="info" class="ml-1">已发布/已归档</el-tag>
              </span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <div class="flex items-center gap-1">
              <el-tag v-if="row.archived" size="small" type="info">已归档</el-tag>
              <el-tag v-else-if="row.review_status === 'approved'" size="small" type="success">已发布</el-tag>
              <el-tag v-else-if="row.review_status === 'pending'" size="small" type="warning">待评审</el-tag>
              <el-tag v-else-if="row.review_status === 'rejected'" size="small" type="danger">已驳回</el-tag>
              <el-tag v-else size="small" type="primary">未评审</el-tag>
              <el-tag v-if="row.status === 1 && !row.archived" size="small" type="success" effect="plain">启用</el-tag>
              <el-tag v-if="row.status === 0 && !row.archived" size="small" type="info" effect="plain">停用</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="最新版本" width="120">
          <template #default="{ row }">
            <span class="inline-flex items-center gap-1">
              <span class="font-bold">v{{ row.version }}</span>
              <el-tag size="small" type="info" effect="plain">{{ row.version_count || 1 }} 个版本</el-tag>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">{{ row.created_at?.slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="goToDetail(row)">进入指标页</el-button>
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

    <!-- Bind Dialog -->
    <FormDialog
      v-model:visible="bindDialog.visible"
      title="新建BOM绑定"
      :form-data="bindForm"
      :rules="bindRules"
      :submitting="submitting"
      @submit="submitBind"
    >
      <template #default="{ form }">
        <el-form-item label="BOM编码" prop="bom_code">
           <el-autocomplete
             v-model="form.bom_code"
             :fetch-suggestions="queryBomCodes"
             placeholder="输入BOM编码（支持已录入编码检索）"
             clearable
             class="w-full"
             @change="checkBindBomCode"
           />
         </el-form-item>
        <el-form-item label="BOM名称" prop="bom_name">
          <el-input v-model="form.bom_name" placeholder="BOM名称" />
        </el-form-item>
        <el-form-item label="绑定集合" prop="collection_id">
          <el-select v-model="form.collection_id" placeholder="选择测试项集合" class="w-full" filterable>
            <el-option
              v-for="c in collections"
              :key="c.id"
              :label="`${c.name} (${c.code})`"
              :value="c.id"
            />
            <template #empty>
              <el-empty description="暂无可选集合，请先在「测试项集合管理」创建并启用" :image-size="50" />
            </template>
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

// ── Data State ──
const bomList = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const collections = ref<any[]>([])
const collectionMap = ref<Record<number, string>>({})

// ── Query ──
const query = reactive({ keyword: '', status: undefined as number | undefined })
function search() { page.value = 1; load() }
function reset() { query.keyword = ''; query.status = undefined; page.value = 1; load() }

// ── Load ──
async function load() {
  loading.value = true
  try {
    const res = await metricsApi.listGroupedBomConfigs({
      page: page.value, page_size: pageSize.value, keyword: query.keyword, status: query.status,
    })
    bomList.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

async function loadCollections() {
  const res = await metricsApi.listAllCollections()
  collections.value = res.data || []
  collectionMap.value = {}
  for (const c of collections.value) {
    collectionMap.value[c.id] = c.name
  }
}

// ── Navigate to BOM 编码指标页面 (一级中转页，含版本选择器 + Tab) ──
function goToDetail(row: any) {
  router.push({
    name: 'BomCodeEdit',
    params: { bomCode: row.bom_code, id: row.id },
  })
}

// ── BOM Code Autocomplete ──
async function queryBomCodes(queryStr: string, cb: (results: any[]) => void) {
  const res = await metricsApi.listBomCodes({ keyword: queryStr })
  cb((res.data || []).map((r: any) => ({ value: r.bom_code, bom_name: r.bom_name })))
}

// ── Bind Dialog ──
const bindDialog = reactive({ visible: false })
const submitting = ref(false)
const bindForm = reactive({ bom_code: '', bom_name: '', collection_id: null as number | null })
const bindRules = {
  bom_code: [{ required: true, message: '请输入BOM编码', trigger: 'blur' }],
  collection_id: [{ required: true, message: '请选择测试项集合', trigger: 'change' }],
}

function openBindDialog() {
  Object.assign(bindForm, { bom_code: '', bom_name: '', collection_id: null })
  bindDialog.visible = true
}

async function checkBindBomCode(code: string) {
  if (!code) return
  try {
    const res = await metricsApi.checkBomVersion(code)
    if (res.data?.has_non_closed) {
      ElMessage.warning('该BOM编码已存在未评审/未归档版本，不允许新增绑定')
    }
  } catch { /* ignore */ }
}

async function submitBind() {
  submitting.value = true
  try {
    await metricsApi.createBomConfig({
      bom_code: bindForm.bom_code,
      bom_name: bindForm.bom_name || '',
      collection_id: bindForm.collection_id!,
    })
    ElMessage.success('BOM绑定创建成功')
    bindDialog.visible = false
    await load()
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '创建失败'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}

// ── Upgrade to Latest Collection Version (with diff preview) ──
async function upgradeToLatest(row: any) {
  try {
    const res = await metricsApi.listVersions({
      entity_type: 'collection',
      entity_id: row.collection_id,
      page_size: 1,
    })
    const latest = res.data?.items?.[0]
    if (!latest) {
      ElMessage.info('暂无版本记录')
      return
    }
    if (latest.version <= (row.collection_version || 0)) {
      ElMessage.info('已是最新版本')
      return
    }
    // 升级前预览差异：新增/删除的测试项
    const previewRes = await metricsApi.previewVersionUpgrade(row.id, latest.id)
    const preview = previewRes.data || {}
    const added = preview.added || []
    const removed = preview.removed || []
    let msg = `确定将 BOM 引用版本从 v${preview.current_version} 升级至最新版 v${preview.target_version} ？\n`
    msg += `（目标版本共 ${preview.target_items} 个测试项）\n`
    if (removed.length) {
      msg += `\n【将移除】${removed.length} 个测试项：\n${removed.slice(0, 10).map((it: any) => `· ${it.process_name || ''}/${it.station || it.station_name || ''} ${it.name}`).join('\n')}${removed.length > 10 ? `\n...等 ${removed.length} 项` : ''}\n`
    }
    if (added.length) {
      msg += `\n【将新增】${added.length} 个测试项：\n${added.slice(0, 10).map((it: any) => `· ${it.process_name || ''}/${it.station || it.station_name || ''} ${it.name}`).join('\n')}${added.length > 10 ? `\n...等 ${added.length} 项` : ''}\n`
    }
    if (!removed.length && !added.length) {
      msg += `\n（测试项结构无变化）`
    }
    await ElMessageBox.confirm(msg, '确认升级', {
      type: 'warning',
      confirmButtonText: '确认升级',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--primary',
    })
    await metricsApi.switchBomVersion(row.id, latest.id)
    ElMessage.success('已升级至最新版本')
    await load()
  } catch { /* cancelled or handled */ }
}

// ── Init ──
onMounted(async () => {
  await Promise.all([load(), loadCollections()])
})
</script>
