<template>
  <div class="min-w-0">
    <div class="flex items-center gap-2 mb-6">
      <el-icon :size="26" color="var(--el-color-primary)"><Timer /></el-icon>
      <div>
        <h1 class="section-title !mb-0 !border-0 !pl-0 text-xl">指标版本记录</h1>
        <div class="section-subtitle mt-0.5">BOM、测试项集合修改指标阈值后自动生成版本快照，支持回滚</div>
      </div>
    </div>

    <!-- Filter -->
    <el-card shadow="hover" class="mb-4 app-card-hover">
      <el-form :inline="true" :model="query" @keyup.enter="search">
        <el-form-item label="实体类型">
          <el-select v-model="query.entity_type" placeholder="全部" clearable style="width:130px" @change="onEntityTypeChange">
            <el-option label="BOM" value="bom" />
            <el-option label="测试项集合" value="collection" />
          </el-select>
        </el-form-item>
        <el-form-item label="搜索">
          <el-input v-model="query.keyword" placeholder="BOM编码 / 变更摘要" clearable style="width:220px" />
        </el-form-item>
        <el-form-item label="操作人">
          <el-input v-model="query.operator" placeholder="操作人" clearable style="width:140px" />
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            clearable
            style="width:260px"
          />
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
          <span class="font-bold">版本历史列表</span>
        </div>
      </template>
      <el-table :data="list" stripe v-loading="loading" style="width:100%">
        <el-table-column label="#" type="index" width="50" />
        <el-table-column label="实体类型" width="110">
          <template #default="{ row }">
            <el-tag :type="row.entity_type === 'bom' ? 'primary' : 'warning'" size="small">
              {{ row.entity_type === 'bom' ? 'BOM' : '测试项集合' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="entity_id" label="实体ID" width="80" />
        <el-table-column prop="version" label="版本号" width="80" />
        <el-table-column prop="change_summary" label="变更摘要" min-width="200" show-overflow-tooltip />
        <el-table-column prop="operator" label="操作人" width="120" />
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">{{ row.created_at?.slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showDetail(row)">详情</el-button>
            <el-button size="small" @click="showDiff(row)" :disabled="!hasPrevVersion(row)">对比</el-button>
            <el-button
              size="small"
              type="warning"
              @click="handleRollback(row)"
            >回滚</el-button>
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

    <!-- Detail Dialog -->
    <el-dialog v-model="detailVisible" title="版本详情" width="700px" top="5vh">
      <template v-if="detailData">
        <div class="mb-3">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="实体类型">{{ detailData.entity_type === 'bom' ? 'BOM' : '测试项集合' }}</el-descriptions-item>
            <el-descriptions-item label="实体ID">{{ detailData.entity_id }}</el-descriptions-item>
            <el-descriptions-item label="版本号">{{ detailData.version }}</el-descriptions-item>
            <el-descriptions-item label="操作人">{{ detailData.operator }}</el-descriptions-item>
            <el-descriptions-item label="变更摘要" :span="2">{{ detailData.change_summary }}</el-descriptions-item>
            <el-descriptions-item label="创建时间" :span="2">{{ detailData.created_at?.slice(0, 16) }}</el-descriptions-item>
          </el-descriptions>
        </div>
        <div v-if="detailData.entity_type === 'bom'">
          <h4 class="font-bold mb-2">BOM 信息</h4>
          <el-descriptions :column="2" border size="small" class="mb-3">
            <el-descriptions-item label="BOM编码">{{ detailData.snapshot_data?.bom_config?.bom_code }}</el-descriptions-item>
            <el-descriptions-item label="BOM名称">{{ detailData.snapshot_data?.bom_config?.bom_name }}</el-descriptions-item>
          </el-descriptions>
          <h4 class="font-bold mb-2">指标列表（共 {{ (detailData.snapshot_data?.indicators || []).length }} 项）</h4>
          <el-table :data="detailData.snapshot_data?.indicators || []" stripe size="small" max-height="400" style="width:100%">
            <el-table-column prop="code" label="指标编码" width="120" />
            <el-table-column prop="name" label="指标名称" width="140" />
            <el-table-column prop="category" label="分类" width="70" />
            <el-table-column label="测试参数" min-width="150">
              <template #default="{ row }">
                <template v-if="row.params">
                  <el-tag v-for="(v, k) in row.params" :key="k" size="small" class="mr-1 mb-1">{{ k }}: {{ v }}</el-tag>
                </template>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="unit" label="单位" width="50" />
            <el-table-column prop="judgment_rule" label="判定规则" width="80" />
            <el-table-column prop="test_stage" label="测试阶段" width="80" />
          </el-table>
        </div>
        <div v-else>
          <h4 class="font-bold mb-2">集合信息</h4>
          <el-descriptions :column="2" border size="small" class="mb-3">
            <el-descriptions-item label="名称">{{ detailData.snapshot_data?.collection?.name }}</el-descriptions-item>
            <el-descriptions-item label="编码">{{ detailData.snapshot_data?.collection?.code }}</el-descriptions-item>
          </el-descriptions>
          <h4 class="font-bold mb-2">测试项列表</h4>
          <el-table :data="detailData.snapshot_data?.items || []" stripe size="small" max-height="400" style="width:100%">
            <el-table-column prop="name" label="测试项名称" width="180" />
            <el-table-column prop="station" label="测试工位" width="140" />
            <el-table-column prop="test_type" label="测试类型" width="100" />
          </el-table>
        </div>
      </template>
    </el-dialog>

    <!-- Diff Dialog -->
    <el-dialog v-model="diffVisible" title="版本对比" width="800px" top="5vh">
      <template v-if="diffData">
        <div class="mb-3">
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="当前版本">{{ diffData.version }}</el-descriptions-item>
            <el-descriptions-item label="对比版本">{{ diffData.prev_version ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="变更摘要">{{ diffData.change_summary }}</el-descriptions-item>
          </el-descriptions>
        </div>
        <el-tabs v-model="diffTab">
          <el-tab-pane :label="`新增 (${diffData.diff?.total_added || 0})`" name="added">
            <el-table :data="diffData.diff?.added || []" stripe size="small" max-height="400" style="width:100%" v-if="(diffData.diff?.added || []).length">
              <el-table-column prop="code" label="指标编码" width="120" />
              <el-table-column prop="name" label="指标名称" width="140" />
              <el-table-column prop="process_name" label="工序" width="120" />
              <el-table-column prop="station_name" label="工位" width="120" />
              <el-table-column prop="unit" label="单位" width="50" />
              <el-table-column prop="judgment_rule" label="判定规则" width="80" />
            </el-table>
            <el-empty v-else description="无新增指标" />
          </el-tab-pane>
          <el-tab-pane :label="`删除 (${diffData.diff?.total_removed || 0})`" name="removed">
            <el-table :data="diffData.diff?.removed || []" stripe size="small" max-height="400" style="width:100%" v-if="(diffData.diff?.removed || []).length">
              <el-table-column prop="code" label="指标编码" width="120" />
              <el-table-column prop="name" label="指标名称" width="140" />
              <el-table-column prop="process_name" label="工序" width="120" />
              <el-table-column prop="station_name" label="工位" width="120" />
              <el-table-column prop="unit" label="单位" width="50" />
              <el-table-column prop="judgment_rule" label="判定规则" width="80" />
            </el-table>
            <el-empty v-else description="无删除指标" />
          </el-tab-pane>
          <el-tab-pane :label="`修改 (${diffData.diff?.total_modified || 0})`" name="modified">
            <template v-if="(diffData.diff?.modified || []).length">
              <div v-for="(item, idx) in diffData.diff?.modified || []" :key="idx" class="mb-4 p-3 rounded" style="background:#f8f9fa">
                <div class="font-bold mb-2">{{ item.item?.code || item.item?.name }} - {{ item.item?.name }} <el-tag size="small" v-if="item.item?.process_name" class="ml-2">{{ item.item.process_name }}</el-tag><el-tag size="small" type="info" v-if="item.item?.station_name" class="ml-1">{{ item.item.station_name }}</el-tag></div>
                <el-table :data="flattenDiffFields(item.diff_fields || {})" stripe size="small" style="width:100%">
                  <el-table-column prop="field" label="变更字段" width="120" />
                  <el-table-column prop="before" label="修改前" width="150">
                    <template #default="{ row: fld }">
                      <span style="color:#e74c3c">{{ fld.before ?? '-' }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="after" label="修改后" width="150">
                    <template #default="{ row: fld }">
                      <span style="color:#27ae60">{{ fld.after ?? '-' }}</span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </template>
            <el-empty v-else description="无修改指标" />
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { metricsApi } from '@/api/metrics'

const route = useRoute()

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const entityId = ref(0)

const query = reactive({
  entity_type: '',
  keyword: '',
  operator: '',
  date_from: '',
  date_to: '',
})
const dateRange = ref<any[]>([])

function search() { page.value = 1; load() }
function reset() {
  query.entity_type = ''
  query.keyword = ''
  query.operator = ''
  query.date_from = ''
  query.date_to = ''
  dateRange.value = []
  entityId.value = 0
  page.value = 1
  load()
}

function onEntityTypeChange() {
  page.value = 1
}

async function load() {
  loading.value = true
  try {
    if (dateRange.value && dateRange.value.length === 2) {
      query.date_from = dateRange.value[0] as string
      query.date_to = dateRange.value[1] as string
    } else {
      query.date_from = ''
      query.date_to = ''
    }
    const params: any = {
      page: page.value,
      page_size: pageSize.value,
      entity_type: query.entity_type,
      keyword: query.keyword || undefined,
      operator: query.operator || undefined,
      date_from: query.date_from || undefined,
      date_to: query.date_to || undefined,
    }
    if (entityId.value > 0) params.entity_id = entityId.value
    const res = await metricsApi.listVersions(params)
    list.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

function hasPrevVersion(row: any) {
  return row.version > 1
}

// ── Detail ──
const detailVisible = ref(false)
const detailData = ref<any>(null)

async function showDetail(row: any) {
  const res = await metricsApi.getVersionDetail(row.id)
  detailData.value = res.data
  detailVisible.value = true
}

// ── Diff ──
const diffVisible = ref(false)
const diffData = ref<any>(null)
const diffTab = ref('added')

function flattenDiffFields(diff_fields: Record<string, any>): Array<{field: string, before: any, after: any}> {
  const result: Array<{field: string, before: any, after: any}> = []
  for (const [fk, df] of Object.entries(diff_fields)) {
    if ('before' in df || 'after' in df) {
      result.push({ field: fk, before: df.before ?? '-', after: df.after ?? '-' })
    } else if (df.added || df.removed || df.modified) {
      for (const p of (df.added || [])) {
        result.push({ field: `${fk}(新增)`, before: '-', after: `${p.name || p.key} = ${p.value ?? ''}` })
      }
      for (const p of (df.removed || [])) {
        result.push({ field: `${fk}(删除)`, before: `${p.name || p.key} = ${p.value ?? ''}`, after: '-' })
      }
      for (const pm of (df.modified || [])) {
        for (const [subFk, subDf] of Object.entries(pm.diff_fields)) {
          const sd = subDf as { before?: any; after?: any }
          result.push({ field: `${fk}(${pm.name}.${subFk})`, before: sd.before ?? '-', after: sd.after ?? '-' })
        }
      }
    }
  }
  return result
}

async function showDiff(row: any) {
  try {
    const res = await metricsApi.getVersionDiff(row.id)
    diffData.value = res.data
    diffTab.value = 'added'
    diffVisible.value = true
  } catch { /* handled */ }
}

// ── Rollback ──
async function handleRollback(row: any) {
  try {
    await ElMessageBox.confirm(
      `确定回滚至版本 ${row.version}？\n当前配置将被替换为快照数据，该操作不可逆。`,
      '回滚确认',
      { confirmButtonText: '确定回滚', cancelButtonText: '取消', type: 'warning' },
    )
    await metricsApi.rollbackVersion(row.id, { operator: '' })
    ElMessage.success('回滚成功')
    await load()
  } catch { /* cancelled or error */ }
}

onMounted(() => {
  // Apply route query params (e.g., from BomConfigView navigation)
  if (route.query.entity_type) query.entity_type = route.query.entity_type as string
  if (route.query.entity_id) {
    // We need to pass entity_id to the list API too; store it in reactive state
    entityId.value = parseInt(route.query.entity_id as string, 10) || 0
  }
  load()
})
</script>
