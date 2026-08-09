<template>
  <div class="min-w-0">
    <div class="flex items-center gap-2 mb-6">
      <el-icon :size="26" color="var(--el-color-primary)"><Odometer /></el-icon>
      <div>
        <h1 class="section-title !mb-0 !border-0 !pl-0 text-xl" style="font-weight:700;font-size:1.25rem">仪表盘</h1>
        <div class="section-subtitle mt-0.5" style="font-weight:600;font-size:0.875rem">测试概览与运行趋势</div>
      </div>
    </div>

    <!-- Stats Cards -->
    <el-row :gutter="20" class="mb-6">
      <el-col :span="6" v-for="card in stats" :key="card.label">
        <el-card shadow="hover" class="text-center">
          <div class="text-3xl font-bold" :style="{ color: card.color }">{{ card.value }}</div>
          <div class="text-gray-500 text-sm mt-2">{{ card.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Charts Row -->
    <el-row :gutter="20" class="mb-6">
      <el-col :span="14">
        <el-card shadow="hover" class="app-card-hover">
          <template #header><span class="font-bold">最近 7 天测试趋势</span></template>
          <v-chart :option="trendOption" style="height: 280px" autoresize />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="hover" class="app-card-hover">
          <template #header><span class="font-bold">测试状态分布</span></template>
          <v-chart :option="pieOption" style="height: 280px" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <!-- Recent Runs + Pending Approvals -->
    <el-row :gutter="20">
      <el-col :span="14">
        <el-card shadow="hover" class="app-card-hover">
          <template #header><span class="font-bold">最近测试记录</span></template>
          <el-table :data="recentRuns" v-loading="runsLoading" style="width: 100%" size="small" max-height="320">
            <el-table-column prop="batch_id" label="批次号" width="180" />
            <el-table-column prop="serial_number" label="序列号" width="130" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="runStatusTag(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="passed_items" label="通过" width="60" />
            <el-table-column prop="failed_items" label="失败" width="60" />
            <el-table-column prop="created_at" label="时间" width="160" />
            <template #empty>
              <div class="flex flex-col items-center py-8 text-gray-400">
                <el-icon :size="34" color="#c0c8d4"><List /></el-icon>
                <div class="mt-2 text-sm">暂无测试记录</div>
              </div>
            </template>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="hover" class="app-card-hover">
          <template #header><span class="font-bold">待审批</span></template>
          <div v-if="pendingList.length === 0" class="text-center text-gray-400 py-8">暂无待审批事项</div>
          <el-timeline v-else>
            <el-timeline-item
              v-for="item in pendingList.slice(0, 5)"
              :key="item.id"
              :timestamp="item.created_at || ''"
              :color="item.type === 'deployment' ? '#E6A23C' : '#409EFF'"
            >
              <p class="text-sm">{{ item.title || item.version || '审批' }}</p>
              <p class="text-xs text-gray-400">{{ item.type === 'deployment' ? '部署审批' : '版本审批' }}</p>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { testApi } from '@/api/test'
import { stationApi } from '@/api/station'
import { versionApi } from '@/api/version'
import { runStatusTag } from '@/utils'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const runsLoading = ref(false)
const recentRuns = ref<any[]>([])
const stats = ref([
  { label: '今日测试', value: '-', color: '#409EFF' },
  { label: '通过率', value: '-', color: '#67C23A' },
  { label: '活跃工站', value: '-', color: '#E6A23C' },
  { label: '待审批', value: '-', color: '#F56C6C' },
])
const pendingList = ref<any[]>([])

const todayStr = ref('')
const sevenDaysAgo = ref('')

function formatDateStr(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function getDatesBetween(start: Date, end: Date): string[] {
  const dates: string[] = []
  const cur = new Date(start)
  while (cur <= end) {
    dates.push(formatDateStr(cur))
    cur.setDate(cur.getDate() + 1)
  }
  return dates
}

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, bottom: 30, top: 10 },
  xAxis: { type: 'category', data: trendDates.value },
  yAxis: { type: 'value', min: 0 },
  series: [
    { name: '总测试', type: 'line', data: trendTotal.value, smooth: true, color: '#409EFF' },
    { name: '通过', type: 'line', data: trendPassed.value, smooth: true, color: '#67C23A' },
    { name: '失败', type: 'line', data: trendFailed.value, smooth: true, color: '#F56C6C' },
  ],
}))

const trendDates = ref<string[]>([])
const trendTotal = ref<number[]>([])
const trendPassed = ref<number[]>([])
const trendFailed = ref<number[]>([])

const pieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    data: [
      { name: '通过', value: piePassed.value, itemStyle: { color: '#67C23A' } },
      { name: '失败', value: pieFailed.value, itemStyle: { color: '#F56C6C' } },
      { name: '运行中', value: pieRunning.value, itemStyle: { color: '#409EFF' } },
      { name: '待处理', value: piePending.value, itemStyle: { color: '#C0C4CC' } },
    ],
  }],
}))

const piePassed = ref(0)
const pieFailed = ref(0)
const pieRunning = ref(0)
const piePending = ref(0)

async function loadDashboard() {
  runsLoading.value = true
  try {
    const now = new Date()
    const today = formatDateStr(now)
    todayStr.value = today

    const weekAgo = new Date(now)
    weekAgo.setDate(weekAgo.getDate() - 6)
    sevenDaysAgo.value = formatDateStr(weekAgo)
    const dates = getDatesBetween(weekAgo, now)
    trendDates.value = dates

    // Today's runs
    const todayRes = await testApi.listRuns({ start_date: today, end_date: today, page: 1, page_size: 1 })
    const todayTotal = todayRes.data?.total || 0
    stats.value[0].value = todayTotal

    // 7-day trend
    const weekRes = await testApi.listRuns({ start_date: formatDateStr(weekAgo), end_date: today, page: 1, page_size: 10000 })
    const allRuns: any[] = weekRes.data?.items || []

    // Group by date
    const dailyMap: Record<string, { total: number; passed: number; failed: number }> = {}
    dates.forEach((d) => { dailyMap[d] = { total: 0, passed: 0, failed: 0 } })
    allRuns.forEach((r: any) => {
      const d = r.created_at ? r.created_at.slice(0, 10) : ''
      if (dailyMap[d]) {
        dailyMap[d].total++
        if (r.status === 'completed') dailyMap[d].passed++
        else if (r.status === 'failed') dailyMap[d].failed++
      }
    })
    trendTotal.value = dates.map((d) => dailyMap[d].total)
    trendPassed.value = dates.map((d) => dailyMap[d].passed)
    trendFailed.value = dates.map((d) => dailyMap[d].failed)

    // Pass rate from today
    const todayRuns = allRuns.filter((r: any) => r.created_at?.slice(0, 10) === today)
    const passed = todayRuns.filter((r: any) => r.status === 'completed').length
    const failed = todayRuns.filter((r: any) => r.status === 'failed').length
    const running = todayRuns.filter((r: any) => r.status === 'running').length
    const pending = todayRuns.filter((r: any) => r.status === 'pending').length
    stats.value[1].value = todayTotal > 0 ? `${Math.round((passed / todayTotal) * 100)}%` : '-'
    piePassed.value = passed
    pieFailed.value = failed
    pieRunning.value = running
    piePending.value = pending

    // Active stations
    const stRes = await stationApi.listStations()
    const allStations = stRes.data || []
    stats.value[2].value = allStations.length

    // Pending approvals
    try {
      const pendRes = await versionApi.pendingApprovals()
      const pendData = pendRes.data || []
      const stepItems = pendData.filter((i: any) => i.type === 'step')
      const depItems = pendData.filter((i: any) => i.type === 'deployment')
      stats.value[3].value = stepItems.length + depItems.length
      pendingList.value = [
        ...stepItems.map((i: any) => ({ ...i.step, type: 'step', title: i.version?.project_name || i.version?.version || '版本审批', created_at: i.step?.created_at || '' })),
        ...depItems.map((i: any) => ({ id: i.dep_id, type: 'deployment', title: i.version?.project_name || i.version?.version || '部署审批', created_at: i.created_at || '' })),
      ]
    } catch {
      stats.value[3].value = '-'
    }

    // Recent runs
    const recentRes = await testApi.listRuns({ page: 1, page_size: 10 })
    recentRuns.value = recentRes.data?.items || []
  } catch (e: any) {
    console.error('加载仪表盘数据失败', e)
  } finally {
    runsLoading.value = false
  }
}

onMounted(loadDashboard)
</script>
