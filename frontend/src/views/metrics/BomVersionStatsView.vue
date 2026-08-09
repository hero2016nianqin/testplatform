<template>
  <div class="min-w-0">
    <!-- Filter -->
    <el-card shadow="hover" class="mb-2 app-card-hover">
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
          <span class="font-bold">版本列表</span>
          <el-button type="primary" size="small" @click="openBindDialog()">
            <el-icon class="mr-1"><Plus /></el-icon>新增绑定
          </el-button>
        </div>
</template>
       <el-table :data="bomList" stripe v-loading="loading" style="width:100%">
         <el-table-column prop="bom_code" label="BOM编码" width="140" />
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
        <el-table-column label="状态" width="70">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="版本" width="60">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" @click="goToDetail(row)">
              {{ row.version }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">{{ row.created_at?.slice(0, 16) }}</template>
        </el-table-column>
<el-table-column label="操作" width="420">
           <template #default="{ row }">
             <el-button size="small" type="primary" @click="goToDetail(row)">查看</el-button>
             <template v-if="row.review_status !== 'approved' && !row.archived">
               <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
               <el-button size="small" @click="openCopyDialog(row)">复制</el-button>
               <el-button size="small" @click="openSwitchVersionDialog(row)">切换版本</el-button>
               <el-button size="small" type="danger" @click="handleDelete(row)">解绑</el-button>
             </template>
             <template v-else>
               <el-button size="small" type="warning" @click="handleCreateIteration(row)">基于此版本新建</el-button>
             </template>
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
           <el-input v-model="form.bom_code" :disabled="true" />
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

    <!-- Edit Dialog -->
    <FormDialog
      v-model:visible="editDialog.visible"
      :title="'编辑BOM绑定'"
      :form-data="editForm"
      :rules="editRules"
      :submitting="submitting"
      @submit="submitEdit"
    >
      <template #default="{ form }">
<el-form-item label="BOM编码" prop="bom_code">
           <el-input v-model="form.bom_code" readonly />
         </el-form-item>
        <el-form-item label="BOM名称" prop="bom_name">
          <el-input v-model="form.bom_name" />
        </el-form-item>
        <el-form-item label="绑定集合" prop="collection_id">
          <el-select v-model="form.collection_id" placeholder="选择测试项集合" class="w-full" filterable>
            <el-option
              v-for="c in collections"
              :key="c.id"
              :label="`${c.name} (${c.code})`"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </template>
    </FormDialog>

    <!-- Copy Dialog -->
    <FormDialog
      v-model:visible="copyDialog.visible"
      title="复制BOM配置"
      :form-data="copyForm"
      :rules="copyRules"
      :submitting="submitting"
      @submit="submitCopy"
    >
      <template #default="{ form }">
        <el-form-item label="目标BOM编码" prop="target_bom_code">
          <el-input v-model="form.target_bom_code" />
        </el-form-item>
        <el-form-item label="目标BOM名称">
          <el-input v-model="form.target_bom_name" />
        </el-form-item>
      </template>
    </FormDialog>

    <!-- Switch Collection Version Dialog -->
    <el-dialog v-model="versionDialog.visible" title="切换集合版本" width="600px" @closed="versionDialog.visible = false">
      <div v-loading="versionDialog.loading">
        <div class="text-sm text-gray-500 mb-3">
          当前集合：<strong>{{ collectionMap[versionDialog.collectionId] || versionDialog.collectionId }}</strong>
        </div>
        <el-table :data="versionList" stripe size="small" style="width:100%" max-height="360">
          <el-table-column label="版本" width="60" align="center">
            <template #default="{ row }">
              <el-tag size="small">{{ row.version }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="变更说明" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ row.change_summary || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作人" width="120">
            <template #default="{ row }">{{ row.operator || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作时间" width="150">
            <template #default="{ row }">{{ row.created_at?.slice(0, 16) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click="confirmSwitchVersion(row)">切换</el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无版本记录" :image-size="50" />
          </template>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { metricsApi } from '@/api/metrics'
import FormDialog from '@/components/FormDialog.vue'

const route = useRoute()
const router = useRouter()

// ── Data State ──
const bomList = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const collections = ref<any[]>([])
const collectionMap = ref<Record<number, string>>({})
const bomCode = computed(() => String(route.params.bomCode || ''))
const versions = ref<any[]>([])

// ── Query ──
const query = reactive({ keyword: '', status: undefined as number | undefined })
function search() { page.value = 1; load() }
function reset() { query.keyword = ''; query.status = undefined; page.value = 1; load() }

// ── Load ──
async function load() {
  loading.value = true
  try {
    const res = await metricsApi.listBomConfigsByCode(bomCode.value)
    const items = res.data || []
    bomList.value = items
    versions.value = items
    total.value = items.length
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

// ── Navigate to BOM Detail Edit (latest version) ──
function goToDetail(row: any) {
  const latest = versions.value[0]
  const targetId = latest?.id || row.id
  router.push({ name: 'BomCodeEdit', params: { bomCode: bomCode.value, id: targetId } })
}

// ── Bind Dialog ──
const bindDialog = reactive({ visible: false })
const submitting = ref(false)
const bindForm = reactive({ bom_code: '', bom_name: '', collection_id: null as number | null })
const bindRules = {
  collection_id: [{ required: true, message: '请选择测试项集合', trigger: 'change' }],
}

function openBindDialog() {
  Object.assign(bindForm, { bom_code: bomCode.value, bom_name: '', collection_id: null })
  bindDialog.visible = true
}

async function submitBind() {
  submitting.value = true
  try {
    await metricsApi.createBomConfig({
      bom_code: bomCode.value,
      bom_name: bindForm.bom_name || '',
      collection_id: bindForm.collection_id!,
    })
    ElMessage.success('BOM绑定创建成功')
    bindDialog.visible = false
    await load()
  } finally {
    submitting.value = false
  }
}

// ── Edit Dialog ──
const editDialog = reactive({ visible: false, editId: 0 })
const editForm = reactive({ bom_code: '', bom_name: '', collection_id: null as number | null, status: 1 })
const editRules = {
  bom_code: [{ required: true, message: '请输入BOM编码', trigger: 'blur' }],
  collection_id: [{ required: true, message: '请选择测试项集合', trigger: 'change' }],
}

function openEditDialog(row: any) {
  editDialog.editId = row.id
  Object.assign(editForm, {
    bom_code: row.bom_code, bom_name: row.bom_name, collection_id: row.collection_id, status: row.status,
  })
  editDialog.visible = true
}

async function submitEdit() {
  submitting.value = true
  try {
    await metricsApi.updateBomConfig(editDialog.editId, { ...editForm })
    ElMessage.success('BOM配置更新成功')
    editDialog.visible = false
    await load()
    const latest = versions.value[0]
    if (latest) {
      router.push({ name: 'BomCodeEdit', params: { bomCode: bomCode.value, id: latest.id } })
    }
  } finally {
    submitting.value = false
  }
}

// ── Copy Dialog ──
const copyDialog = reactive({ visible: false, configId: 0 })
const copyForm = reactive({ target_bom_code: '', target_bom_name: '' })
const copyRules = {
  target_bom_code: [{ required: true, message: '请输入目标BOM编码', trigger: 'blur' }],
}

function openCopyDialog(row: any) {
  copyDialog.configId = row.id
  Object.assign(copyForm, { target_bom_code: '', target_bom_name: '' })
  copyDialog.visible = true
}

async function submitCopy() {
  submitting.value = true
  try {
    await metricsApi.copyBomConfig(copyDialog.configId, { ...copyForm })
    ElMessage.success('BOM配置复制成功')
    copyDialog.visible = false
    await load()
  } finally {
    submitting.value = false
  }
}

// ── Create New Iteration from Published/Archived Version ──
async function handleCreateIteration(row: any) {
  try {
    await ElMessageBox.confirm(
      `将基于已${row.archived ? '归档' : '发布'}的 v${row.version} 创建新迭代\n\nBOM编码: ${row.bom_code}\n当前版本: v${row.version}\n\n新版本将复制所有指标和参数数据，生成未评审的迭代版本继续编辑？`,
      '基于此版本新建',
    )
    const res = await metricsApi.createNewIteration(row.id)
    const newId = res.data?.id
    ElMessage.success(`新迭代版本 v${res.data?.version} 已创建`)
    await load()
    if (newId) {
      router.push({ name: 'BomCodeEdit', params: { bomCode: bomCode.value, id: newId } })
    }
  } catch (e: any) {
    if (e?.response?.data?.message) {
      ElMessage.error(e.response.data.message)
    } else if (e?.message && e.message !== 'cancel' && e.message !== '取消') {
      ElMessage.error(e.message)
    }
  }
}

// ── Delete ──
async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定解绑 BOM "${row.bom_code}"？`, '确认')
    await metricsApi.deleteBomConfig(row.id)
    ElMessage.success('BOM配置已删除')
    await load()
  } catch { /* cancelled */ }
}

// ── Switch Collection Version (BOM only — never touches collection) ──
const versionDialog = reactive({ visible: false, loading: false, collectionId: 0, configId: 0 })
const versionList = ref<any[]>([])

async function openSwitchVersionDialog(row: any) {
  versionDialog.collectionId = row.collection_id
  versionDialog.configId = row.id
  versionDialog.loading = true
  versionDialog.visible = true
  versionList.value = []
  try {
    const res = await metricsApi.listVersions({
      entity_type: 'collection',
      entity_id: row.collection_id,
      page_size: 200,
    })
    versionList.value = res.data?.items || []
  } finally {
    versionDialog.loading = false
  }
}

async function confirmSwitchVersion(snapshot: any) {
  try {
    await ElMessageBox.confirm(
      `确定将 BOM 引用版本切换至 v${snapshot.version} ？`,
      '确认切换',
    )
    await metricsApi.switchBomVersion(versionDialog.configId, snapshot.id)
    ElMessage.success(`已切换至版本 v${snapshot.version}`)
    versionDialog.visible = false
    await load()
  } catch { /* cancelled or handled */ }
}

// ── Upgrade to Latest Version ──
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
    await ElMessageBox.confirm(
      `确定将 BOM 引用版本升级至最新版 v${latest.version} ？`,
      '确认升级',
    )
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