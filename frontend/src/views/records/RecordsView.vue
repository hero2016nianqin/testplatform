<template>
  <div class="min-w-0">
    <div class="flex items-center gap-2 mb-6">
      <el-icon :size="26" color="var(--el-color-primary)"><Document /></el-icon>
      <div>
        <h1 class="section-title !mb-0 !border-0 !pl-0 text-xl" style="font-weight:700;font-size:1.25rem">测试记录</h1>
        <div class="section-subtitle mt-0.5" style="font-weight:600;font-size:0.875rem">测试执行记录与明细查询</div>
      </div>
    </div>

    <!-- Level Tabs -->
    <el-card shadow="hover" class="mb-4 app-card-hover">
      <el-radio-group v-model="level" @change="search">
        <el-radio-button value="R1">R1 — 测试批次</el-radio-button>
        <el-radio-button value="R2">R2 — 含结果</el-radio-button>
        <el-radio-button value="R3">R3 — 含详细日志</el-radio-button>
      </el-radio-group>
    </el-card>

    <!-- Filters -->
    <el-card shadow="hover" class="mb-4 app-card-hover">
      <el-form :inline="true" :model="filters" size="small" class="overflow-hidden">
        <el-form-item label="批次号">
          <el-input v-model="filters.batch_id" placeholder="批次号" style="width: 160px" />
        </el-form-item>
        <el-form-item label="序列号">
          <el-input v-model="filters.serial_number" placeholder="序列号" style="width: 140px" />
        </el-form-item>
        <el-form-item label="操作员">
          <el-input v-model="filters.operator" placeholder="操作员" style="width: 120px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部" style="width: 100px">
            <el-option label="待处理" value="pending" />
            <el-option label="运行中" value="running" />
            <el-option label="完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item label="工站 ID">
          <el-input v-model="filters.station_id" placeholder="工站 ID" style="width: 100px" />
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search"><el-icon class="mr-1"><Search /></el-icon>查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button @click="exportCSV">导出 CSV</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Table -->
    <el-card shadow="hover" class="app-card-hover">
      <el-table :data="records" v-loading="loading" stripe style="width: 100%" size="small" max-height="520">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="batch_id" label="批次号" width="170" />
        <el-table-column prop="serial_number" label="序列号" width="130" />
        <el-table-column prop="operator" label="操作员" width="90" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="runStatusTag(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_items" label="总数" width="60" />
        <el-table-column prop="passed_items" label="通过" width="60" />
        <el-table-column prop="failed_items" label="失败" width="60" />
        <el-table-column prop="sequence_name" label="序列" min-width="100" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" width="160" />

        <!-- R2/R3: expand result details -->
        <el-table-column v-if="level !== 'R1'" type="expand" width="40">
          <template #default="{ row }">
            <div class="p-3">
              <el-table :data="row.results || []" size="small" stripe>
                <el-table-column prop="item_name" label="测试项" min-width="120" />
                <el-table-column prop="actual_value" label="实测值" width="100" />
                <el-table-column prop="expected_value" label="期望值" width="100" />
                <el-table-column prop="passed" label="结果" width="70">
                  <template #default="{ row: r }">
                    <el-tag :type="r.passed ? 'success' : 'danger'" size="small">
                      {{ r.passed ? 'PASS' : 'FAIL' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="duration_ms" label="耗时(ms)" width="90" />
                <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
              </el-table>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <div class="flex flex-col items-center py-8 text-gray-400">
            <el-icon :size="34" color="#c0c8d4"><Document /></el-icon>
            <div class="mt-2 text-sm">暂无测试记录</div>
          </div>
        </template>
      </el-table>

      <div class="flex items-center justify-between mt-3">
        <span class="text-sm text-gray-600">共 {{ total }} 条记录</span>
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchRecords"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { testApi } from '@/api/test'
import { runStatusTag } from '@/utils'

const loading = ref(false)
const level = ref('R1')
const records = ref<any[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dateRange = ref<string[]>([])

const filters = reactive({
  batch_id: '', operator: '', serial_number: '', status: '', station_id: '',
})

function buildParams() {
  const params: any = {
    level: level.value,
    page: page.value,
    page_size: pageSize.value,
  }
  if (filters.batch_id) params.batch_id = filters.batch_id
  if (filters.operator) params.operator = filters.operator
  if (filters.serial_number) params.serial_number = filters.serial_number
  if (filters.status) params.status = filters.status
  if (filters.station_id) params.station_id = Number(filters.station_id)
  if (dateRange.value?.length === 2) {
    params.start_date = dateRange.value[0]
    params.end_date = dateRange.value[1]
  }
  return params
}

async function fetchRecords() {
  loading.value = true
  try {
    const res = await testApi.getRecords(buildParams())
    records.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (e: any) {
    ElMessage.error('加载测试记录失败: ' + (e?.message || ''))
    records.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  fetchRecords()
}

function resetFilters() {
  Object.assign(filters, { batch_id: '', operator: '', serial_number: '', status: '', station_id: '' })
  dateRange.value = []
  page.value = 1
  fetchRecords()
}

async function exportCSV() {
  const params = buildParams()
  params.page = 1
  params.page_size = 200
  try {
    const res = await testApi.getRecords(params)
    const items = res.data?.items || []
    const headers = '批次号,序列号,操作员,状态,总数,通过,失败,时间\n'
    const rows = items.map((r: any) =>
      [r.batch_id, r.serial_number, r.operator, r.status, r.total_items, r.passed_items, r.failed_items, r.created_at].join(',')
    ).join('\n')
    const blob = new Blob(['\uFEFF' + headers + rows], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `records_${level.value}_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    ElMessage.error('导出CSV失败: ' + (e?.message || ''))
  }
}

onMounted(fetchRecords)
</script>
