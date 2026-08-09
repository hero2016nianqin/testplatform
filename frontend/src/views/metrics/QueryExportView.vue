<template>
  <div class="min-w-0">
    <div class="flex items-center gap-2 mb-6">
      <el-icon :size="26" color="var(--el-color-primary)"><Download /></el-icon>
      <div>
        <h1 class="section-title !mb-0 !border-0 !pl-0 text-xl">指标查询导出</h1>
        <div class="section-subtitle mt-0.5">多条件联合查询与导出</div>
      </div>
    </div>

    <!-- Filter -->
    <el-card shadow="hover" class="mb-4 app-card-hover">
      <el-form :inline="true" :model="query" @keyup.enter="search">
        <el-form-item label="BOM编码">
          <el-input v-model="query.bom_code" placeholder="BOM编码" clearable style="width:160px" />
        </el-form-item>
        <el-form-item label="绑定集合">
          <el-select v-model="query.collection_id" placeholder="全部" clearable style="width:180px" filterable>
            <el-option v-for="c in collections" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="指标名称">
          <el-input v-model="query.indicator_name" placeholder="指标名称" clearable style="width:160px" />
        </el-form-item>
        <el-form-item label="产品类型">
          <el-input v-model="query.product_type" placeholder="产品类型" clearable style="width:140px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search"><el-icon class="mr-1"><Search /></el-icon>查询</el-button>
          <el-button @click="reset">重置</el-button>
          <el-button type="success" @click="handleExport" :loading="exporting">
            <el-icon class="mr-1"><Download /></el-icon>{{ exporting ? '导出中...' : '导出Excel' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Result Table -->
    <el-card shadow="hover" class="app-card-hover">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-bold">查询结果（{{ total }} 条）</span>
        </div>
      </template>
      <el-table :data="list" stripe v-loading="loading" style="width:100%">
        <el-table-column prop="bom_code" label="BOM编码" width="120" />
        <el-table-column prop="bom_name" label="BOM名称" width="160" show-overflow-tooltip />
        <el-table-column prop="collection_name" label="绑定集合" width="140" />
        <el-table-column prop="indicator_code" label="指标编码" width="120" />
        <el-table-column prop="indicator_name" label="指标名称" width="140" />
        <el-table-column prop="category" label="分类" width="80" />
        <el-table-column label="测试参数" min-width="150">
          <template #default="{ row }">
            <template v-if="row.params">
              <el-tag v-for="(v, k) in row.params" :key="k" size="small" class="mr-1 mb-1">{{ k }}: {{ v }}</el-tag>
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="60" />
        <el-table-column prop="judgment_rule" label="判定规则" width="80" />
        <el-table-column prop="test_stage" label="测试阶段" width="80" />
      </el-table>
      <div class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @change="load"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { metricsApi } from '@/api/metrics'

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const exporting = ref(false)

const collections = ref<any[]>([])

const query = reactive({
  bom_code: '',
  collection_id: undefined as number | undefined,
  indicator_name: '',
  product_type: '',
})

function search() { page.value = 1; load() }
function reset() {
  query.bom_code = ''
  query.collection_id = undefined
  query.indicator_name = ''
  query.product_type = ''
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (query.bom_code) params.bom_code = query.bom_code
    if (query.collection_id) params.collection_id = query.collection_id
    if (query.indicator_name) params.indicator_name = query.indicator_name
    if (query.product_type) params.product_type = query.product_type
    const res = await metricsApi.queryIndicators(params)
    list.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

async function handleExport() {
  exporting.value = true
  try {
    const params: any = {}
    if (query.bom_code) params.bom_code = query.bom_code
    if (query.collection_id) params.collection_id = query.collection_id
    if (query.indicator_name) params.indicator_name = query.indicator_name
    if (query.product_type) params.product_type = query.product_type
    const blob = await metricsApi.exportIndicators(params) as unknown as Blob
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `indicators_${Date.now()}.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  const res = await metricsApi.listAllCollections()
  collections.value = res.data || []
  load()
})
</script>
