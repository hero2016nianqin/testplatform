<template>
  <div class="version-detail" v-loading="loading">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <el-button @click="$router.back()" text>
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <el-icon :size="28" color="var(--el-color-primary)"><Box /></el-icon>
        <div>
          <h1 class="text-xl font-bold !mb-0">{{ version.project_name }} - {{ version.version }}</h1>
          <div class="text-sm text-gray-500">{{ version.description || '无描述' }}</div>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <el-tag :type="statusType(version.status)" size="large">{{ statusLabel(version.status) }}</el-tag>
        <el-tag v-if="version.type" size="large" type="info">{{ typeLabel(version.type) }}</el-tag>
      </div>
    </div>

    <!-- Basic Info -->
    <el-card class="mb-4">
      <template #header><span class="font-bold">基本信息</span></template>
      <el-descriptions :column="4" border size="small">
        <el-descriptions-item label="版本号">{{ version.version }}</el-descriptions-item>
        <el-descriptions-item label="项目名称">{{ version.project_name }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ typeLabel(version.type) }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusLabel(version.status) }}</el-descriptions-item>
        <el-descriptions-item label="BOM编码">{{ version.bom_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="工艺类型">{{ version.process_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="工位">{{ version.workstation || '-' }}</el-descriptions-item>
        <el-descriptions-item label="域标签">{{ version.domain_tags || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建人">{{ version.created_by }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(version.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatTime(version.updated_at) }}</el-descriptions-item>
        <el-descriptions-item label="继承版本">{{ version.inherit_from_id ? `#${version.inherit_from_id}` : '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- Approval Workflow -->
    <el-card class="mb-4" v-if="version.steps?.length">
      <template #header><span class="font-bold">审批流程</span></template>
      <el-timeline>
        <el-timeline-item
          v-for="step in version.steps"
          :key="step.id"
          :type="stepStatusType(step.status)"
          :timestamp="formatTime(step.approved_at)"
          placement="top"
        >
          <div class="flex items-center justify-between">
            <div>
              <span class="font-bold">{{ step.step_name }}</span>
              <el-tag :type="stepStatusType(step.status)" size="small" class="ml-2">
                {{ stepStatusLabel(step.status) }}
              </el-tag>
            </div>
            <div class="text-sm text-gray-500">
              审批人: {{ step.assigned_to || '-' }}
            </div>
          </div>
          <div v-if="step.comment" class="mt-2 text-sm text-gray-600">
            意见: {{ step.comment }}
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <!-- Archive Items -->
    <el-card class="mb-4" v-if="version.archive_items?.length">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-bold">归档内容</span>
          <el-tag size="small">{{ version.archive_items.length }} 项</el-tag>
        </div>
      </template>

      <!-- Test Items -->
      <div v-if="testItems.length" class="mb-4">
        <h4 class="text-sm font-bold text-gray-600 mb-2">测试项 ({{ testItems.length }})</h4>
        <el-table :data="testItems" size="small" stripe max-height="300">
          <el-table-column prop="item_id" label="ID" width="60" />
          <el-table-column label="测试项名称" min-width="200">
            <template #default="{ row }">
              {{ row.data_snapshot?.name || row.data_snapshot?.test_item_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="期望值" width="100">
            <template #default="{ row }">
              {{ row.data_snapshot?.expected_value || row.data_snapshot?.expected || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="单位" width="60">
            <template #default="{ row }">
              {{ row.data_snapshot?.unit || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="类别" width="100">
            <template #default="{ row }">
              {{ row.data_snapshot?.category || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="是否关键" width="80">
            <template #default="{ row }">
              <el-tag :type="row.data_snapshot?.is_critical ? 'danger' : 'info'" size="small">
                {{ row.data_snapshot?.is_critical ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Sequence Steps -->
      <div v-if="sequenceSteps.length">
        <h4 class="text-sm font-bold text-gray-600 mb-2">测试序列 ({{ sequenceSteps.length }} 步)</h4>
        <el-table :data="sequenceSteps" size="small" stripe max-height="300">
          <el-table-column prop="step_order" label="步骤" width="60" />
          <el-table-column label="测试项" min-width="200">
            <template #default="{ row }">
              {{ row.data_snapshot?.template_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="服务地址" width="180">
            <template #default="{ row }">
              {{ row.data_snapshot?.template_service_address || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="超时(秒)" width="80">
            <template #default="{ row }">
              {{ row.data_snapshot?.timeout_seconds || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="关键" width="60">
            <template #default="{ row }">
              <el-tag :type="row.data_snapshot?.template_is_critical ? 'danger' : 'info'" size="small">
                {{ row.data_snapshot?.template_is_critical ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="类别" width="80">
            <template #default="{ row }">
              {{ row.data_snapshot?.template_category || '-' }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Other Archive Items -->
      <div v-if="otherArchiveItems.length" class="mt-4">
        <h4 class="text-sm font-bold text-gray-600 mb-2">其他归档 ({{ otherArchiveItems.length }})</h4>
        <el-table :data="otherArchiveItems" size="small" stripe max-height="200">
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="item_id" label="项目ID" width="80" />
          <el-table-column label="数据预览" min-width="300">
            <template #default="{ row }">
              <span class="text-xs text-gray-500">{{ JSON.stringify(row.data_snapshot).slice(0, 100) }}...</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- Sub Scenarios -->
    <el-card class="mb-4" v-if="version.sub_scenarios?.length">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-bold">子场景配置</span>
          <el-tag size="small">{{ version.sub_scenarios.length }} 个</el-tag>
        </div>
      </template>

      <el-collapse v-model="activeSubScenario">
        <el-collapse-item
          v-for="ss in version.sub_scenarios"
          :key="ss.id"
          :name="ss.id"
          :title="`${ss.name} - ${ss.process_type} / ${ss.workstation}`"
        >
          <div class="grid grid-cols-2 gap-4">
            <!-- Hardware Params -->
            <div v-if="ss.hardware_params?.length">
              <h5 class="text-sm font-bold text-gray-600 mb-2">硬件参数</h5>
              <el-table :data="ss.hardware_params" size="small" stripe max-height="200">
                <el-table-column prop="name" label="参数名" />
                <el-table-column prop="value" label="值" />
                <el-table-column prop="unit" label="单位" width="60" />
              </el-table>
            </div>

            <!-- Software Metrics -->
            <div v-if="ss.software_metrics?.length">
              <h5 class="text-sm font-bold text-gray-600 mb-2">软件指标</h5>
              <el-table :data="ss.software_metrics" size="small" stripe max-height="200">
                <el-table-column prop="name" label="指标名" />
                <el-table-column prop="value" label="值" />
                <el-table-column prop="unit" label="单位" width="60" />
              </el-table>
            </div>

            <!-- Property Page -->
            <div v-if="ss.property_page?.length">
              <h5 class="text-sm font-bold text-gray-600 mb-2">属性页</h5>
              <el-table :data="ss.property_page" size="small" stripe max-height="200">
                <el-table-column prop="name" label="属性名" />
                <el-table-column prop="value" label="值" />
              </el-table>
            </div>

            <!-- BOM Snapshot -->
            <div v-if="ss.bom_snapshot?.length">
              <h5 class="text-sm font-bold text-gray-600 mb-2">BOM指标快照</h5>
              <el-tree
                :data="ss.bom_snapshot"
                :props="{ label: 'name', children: 'children' }"
                default-expand-all
                :expand-on-click-node="false"
                class="max-h-64 overflow-auto"
              />
            </div>
          </div>

          <!-- Sub Scenario Files -->
          <div v-if="getSubScenarioFiles(ss.id).length" class="mt-4">
            <h5 class="text-sm font-bold text-gray-600 mb-2">附件文件</h5>
            <div class="flex flex-wrap gap-2">
              <el-tag
                v-for="file in getSubScenarioFiles(ss.id)"
                :key="file.id"
                size="small"
                type="info"
              >
                {{ file.filename }}
                <span class="text-gray-400 ml-1">({{ formatFileSize(file.file_size) }})</span>
                <el-button link type="primary" size="small" class="ml-1" @click="downloadFile(file)">
                  <el-icon><Download /></el-icon>
                </el-button>
              </el-tag>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- Binary Files -->
    <el-card class="mb-4" v-if="version.binary_files?.length">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-bold">程序文件</span>
          <el-tag size="small">{{ version.binary_files.length }} 个</el-tag>
        </div>
      </template>
      <el-table :data="version.binary_files" size="small" stripe>
        <el-table-column prop="filename" label="文件名" min-width="200" />
        <el-table-column label="文件大小" width="100">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="文件类型" width="100">
          <template #default="{ row }">
            {{ row.file_type || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="downloadFile(row)">
              <el-icon><Download /></el-icon> 下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Deployments -->
    <el-card class="mb-4" v-if="version.deployments?.length">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-bold">部署记录</span>
          <el-tag size="small">{{ version.deployments.length }} 条</el-tag>
        </div>
      </template>
      <el-table :data="version.deployments" size="small" stripe>
        <el-table-column prop="factory_name" label="工厂" width="120" />
        <el-table-column prop="line_name" label="产线" width="120" />
        <el-table-column prop="station_name" label="工站" min-width="150" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'pending' ? 'warning' : 'info'" size="small">
              {{ deployStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="assigned_to" label="审批人" width="100" />
        <el-table-column prop="approved_by" label="审批人" width="100">
          <template #default="{ row }">
            {{ row.approved_by || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="审批时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.approved_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="comment" label="审批意见" min-width="150">
          <template #default="{ row }">
            {{ row.comment || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="部署时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.deployed_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Empty State -->
    <el-empty v-if="!loading && !version.id" description="版本不存在" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { versionApi } from '@/api/version'
import { ArrowLeft, Box, Download } from '@element-plus/icons-vue'

const route = useRoute()
const loading = ref(false)
const version = ref<any>({})
const activeSubScenario = ref<number[]>([])

const versionId = computed(() => Number(route.params.id))

// Computed properties for archive items
const testItems = computed(() => {
  return (version.value.archive_items || []).filter((item: any) => item.type === 'test_item')
})

const sequenceSteps = computed(() => {
  return (version.value.archive_items || [])
    .filter((item: any) => item.type === 'sequence_step')
    .sort((a: any, b: any) => (a.data_snapshot?.step_order || 0) - (b.data_snapshot?.step_order || 0))
})

const otherArchiveItems = computed(() => {
  return (version.value.archive_items || []).filter(
    (item: any) => item.type !== 'test_item' && item.type !== 'sequence_step'
  )
})

// Helper functions
function statusType(status: string): string {
  const map: Record<string, string> = {
    draft: 'info', released: 'warning', deployed: 'success', delisted: 'danger',
  }
  return map[status] || 'info'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    draft: '草稿', released: '已发布', deployed: '已发行', delisted: '已下架',
  }
  return map[status] || status
}

function typeLabel(type: string): string {
  const map: Record<string, string> = {
    standard: '标准', multi_process: '多工序版本', product_family: '产品族版本',
  }
  return map[type] || type
}

function stepStatusType(status: string): string {
  const map: Record<string, string> = {
    pending: 'warning', approved: 'success', rejected: 'danger',
  }
  return map[status] || 'info'
}

function stepStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '待审批', approved: '已通过', rejected: '已驳回',
  }
  return map[status] || status
}

function deployStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '待审批', approved: '已审批', deployed: '已部署', rejected: '已驳回',
  }
  return map[status] || status
}

function formatTime(time: string | null): string {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN', { hour12: false })
}

function formatFileSize(size: number | null): string {
  if (!size) return '-'
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
  return (size / 1024 / 1024).toFixed(1) + ' MB'
}

function getSubScenarioFiles(ssId: number): any[] {
  return (version.value.binary_files || []).filter((f: any) => f.sub_scenario_id === ssId)
}

function downloadFile(file: any) {
  const url = versionApi.downloadBinaryUrl(versionId.value, file.id)
  window.open(url, '_blank')
}

// Load data
async function loadVersion() {
  loading.value = true
  try {
    const res = await versionApi.get(versionId.value)
    version.value = res.data || {}
    // Auto-expand first sub-scenario
    if (version.value.sub_scenarios?.length) {
      activeSubScenario.value = [version.value.sub_scenarios[0].id]
    }
  } catch (e) {
    console.error('Failed to load version:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadVersion()
})
</script>

<style scoped>
.version-detail {
  padding: 20px;
}
</style>
