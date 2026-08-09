<template>
  <div class="min-w-0">
    <div class="flex items-center gap-2 mb-6">
      <el-icon :size="26" color="#E6A23C"><WarningFilled /></el-icon>
      <div>
        <h1 class="section-title !mb-0 !border-0 !pl-0 text-xl">指标引用中心</h1>
        <div class="section-subtitle mt-0.5">查看全局指标引用情况，追踪高频使用指标</div>
      </div>
    </div>

    <!-- Filter -->
    <el-card shadow="hover" class="mb-4 app-card-hover">
      <el-form :inline="true" :model="query" @keyup.enter="search">
        <el-form-item label="搜索">
          <el-input v-model="query.keyword" placeholder="指标名称/编码" clearable style="width:240px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search"><el-icon class="mr-1"><Search /></el-icon>搜索</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Table -->
    <el-card shadow="hover" class="app-card-hover">
      <template #header><span class="font-bold">指标列表</span></template>
      <el-table :data="list" stripe v-loading="loading" style="width:100%">
        <el-table-column prop="code" label="指标编码" width="120" />
        <el-table-column prop="name" label="指标名称" width="150" />
        <el-table-column prop="unit" label="单位" width="60" />
        <el-table-column prop="category" label="分类" width="80" />
        <el-table-column prop="hardware_model" label="硬件型号" width="100" />
        <el-table-column label="引用-测试项" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.ref_test_items || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="引用-BOM" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.ref_bom_configs || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="70">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="150">
          <template #default="{ row }">{{ row.updated_at?.slice(0, 16) }}</template>
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { metricsApi } from '@/api/metrics'

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const query = reactive({ keyword: '' })

function search() { page.value = 1; load() }
function reset() { query.keyword = ''; page.value = 1; load() }

async function load() {
  loading.value = true
  try {
    const res = await metricsApi.listAlertIndicators({
      keyword: query.keyword,
      page: page.value,
      page_size: pageSize.value,
    })
    list.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
