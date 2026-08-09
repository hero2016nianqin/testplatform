<template>
  <div class="tool-panel" :class="{ collapsed: isCollapsed }">
    <!-- Collapsed: vertical icon bar -->
    <div v-if="isCollapsed" class="icon-bar">
      <el-tooltip content="批量工具" placement="left" :show-after="200">
        <span class="icon-btn" @click="expandTo('batch-tools')"><el-icon><Edit /></el-icon></span>
      </el-tooltip>
      <el-tooltip content="导出 & 统计" placement="left" :show-after="200">
        <span class="icon-btn" @click="expandTo('export-stats')"><el-icon><Download /></el-icon></span>
      </el-tooltip>
      <div class="flex-1" />
      <el-tooltip content="展开工具箱" placement="left" :show-after="200">
        <span class="icon-btn" @click="isCollapsed = false"><el-icon><DArrowLeft /></el-icon></span>
      </el-tooltip>
    </div>

    <!-- Expanded: header + tabs -->
    <template v-else>
      <div class="panel-header">
        <span class="panel-title">工具箱</span>
        <el-button text @click="toggleCollapse">
          <el-icon><DArrowRight /></el-icon>
        </el-button>
      </div>

      <div class="panel-body">
        <el-tabs v-model="activeTab" @tab-change="onTabChange">
          <!-- Tab 1: 批量工具 -->
          <el-tab-pane label="批量工具" name="batch-tools">
            <div class="tab-content">
              <div class="section">
                <label class="section-label">批量填充阈值</label>
                <div class="fill-inputs">
                  <el-input v-model="batchFill.upper" size="small" placeholder="上限" />
                  <el-input v-model="batchFill.lower" size="small" placeholder="下限" />
                </div>
                <el-button size="small" type="primary" class="w-full mt-1" @click="handleBatchFill" :disabled="!batchFill.upper && !batchFill.lower">
                  一键填充
                </el-button>
              </div>
              <el-divider />
              <div class="section">
                <el-button size="small" type="primary" class="w-full" @click="emit('copy-selected')">
                  <el-icon><CopyDocument /></el-icon>复制选中参数
                </el-button>
                <el-button size="small" class="w-full mt-1" @click="emit('paste-to-selected')">
                  <el-icon><DocumentAdd /></el-icon>粘贴到选中项
                </el-button>
                <el-button size="small" class="w-full mt-1" @click="handleClearSelected">
                  <el-icon><Delete /></el-icon>清空选中参数
                </el-button>
                <el-button size="small" class="w-full mt-1" @click="emit('filter-empty')">
                  <el-icon><Search /></el-icon>筛选空白参数
                </el-button>
              </div>
              <el-divider />
              <div class="section">
                <el-button size="small" class="w-full" @click="handleCopyPrevProcess">
                  <el-icon><CopyDocument /></el-icon>复制上工序
                </el-button>
                <el-button size="small" class="w-full mt-1" @click="handleCopyPrevStation">
                  <el-icon><CopyDocument /></el-icon>复制上工位
                </el-button>
              </div>
            </div>
          </el-tab-pane>

          <!-- Tab 2: 导出 & 统计 -->
          <el-tab-pane label="导出 & 统计" name="export-stats">
            <div class="tab-content">
              <div class="section">
                <label class="section-label">填写进度</label>
                <el-progress :percentage="fillPercent" :stroke-width="14" status="success" />
              </div>
              <el-divider />
              <div class="section">
                <label class="section-label">统计概览</label>
                <div class="stats-grid">
                  <div class="stat-item">
                    <span class="stat-num">{{ stats.totalItems }}</span>
                    <span class="stat-label">测试项</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-num">{{ stats.totalParams }}</span>
                    <span class="stat-label">总参数</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-num success">{{ stats.filledCount }}</span>
                    <span class="stat-label">已填写</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-num danger">{{ stats.emptyCount }}</span>
                    <span class="stat-label">未填写</span>
                  </div>
                </div>
              </div>
              <el-divider />
              <div class="section">
                <label class="section-label">维度统计</label>
                <el-radio-group v-model="dimensionKey" size="small" class="w-full mb-1">
                  <el-radio-button label="byProcess">工序</el-radio-button>
                  <el-radio-button label="byStation">工位</el-radio-button>
                  <el-radio-button label="byOwner">负责人</el-radio-button>
                </el-radio-group>
                <el-table :data="dimensionRows" size="small" max-height="220" style="width:100%">
                  <el-table-column label="维度" min-width="90" show-overflow-tooltip>
                    <template #default="{ row }">{{ row.name }}</template>
                  </el-table-column>
                  <el-table-column label="总参" width="56" align="center">
                    <template #default="{ row }">{{ row.total }}</template>
                  </el-table-column>
                  <el-table-column label="未填" width="56" align="center">
                    <template #default="{ row }"><span :class="row.empty ? 'text-danger font-medium' : ''">{{ row.empty }}</span></template>
                  </el-table-column>
                  <el-table-column label="完成率" min-width="80">
                    <template #default="{ row }">
                      <el-progress :percentage="row.percent" :stroke-width="8" :status="row.percent === 100 ? 'success' : undefined" />
                    </template>
                  </el-table-column>
                </el-table>
              </div>
              <el-divider />
              <div class="section">
                <label class="section-label">维度导出</label>
                <el-radio-group v-model="exportDimension" size="small" class="w-full">
                  <el-radio label="bom">全 BOM</el-radio>
                  <el-radio label="process">按工序</el-radio>
                  <el-radio label="station">按工位</el-radio>
                </el-radio-group>
                <el-button size="small" class="w-full mt-1" @click="emit('export-config', exportDimension)">
                  <el-icon><Download /></el-icon>导出当前配置 ({{ exportDimension === 'bom' ? '全BOM' : exportDimension === 'process' ? '工序' : '工位' }})
                </el-button>
                <el-button size="small" class="w-full mt-1" @click="emit('export-template')">
                  <el-icon><DocumentAdd /></el-icon>导出空白模板
                </el-button>
              </div>
              <el-divider />
              <div class="section">
                <label class="section-label">报告 & 导入</label>
                <el-button size="small" class="w-full" @click="emit('export-diff-report')">
                  <el-icon><DataAnalysis /></el-icon>导出差异报告
                </el-button>
                <el-button size="small" class="w-full mt-1" @click="emit('export-pdf')">
                  <el-icon><Download /></el-icon>导出 PDF 评审配置单
                </el-button>
                <el-button size="small" type="primary" class="w-full mt-1" @click="emit('import-excel')">
                  <el-icon><Upload /></el-icon>Excel 导入
                </el-button>
              </div>
              <el-divider />
              <div class="section">
                <label class="section-label">版本变更备注</label>
                <el-input
                  v-model="changeNote"
                  type="textarea"
                  :rows="3"
                  placeholder="请输入版本变更说明..."
                  size="small"
                />
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import {
  CopyDocument, DocumentAdd, Delete, Search, Download, Upload,
  DataAnalysis, DArrowLeft, DArrowRight, Edit,
} from '@element-plus/icons-vue'

const props = defineProps<{
  bom: any
  fillPercent: number
  bomStats?: { totalItems: number; totalParams: number; filledCount: number; emptyCount: number }
  expanded?: boolean
  dimensionStats?: {
    byProcess: { name: string; total: number; empty: number; filled: number; percent: number }[]
    byStation: { name: string; total: number; empty: number; filled: number; percent: number }[]
    byOwner: { name: string; total: number; empty: number; filled: number; percent: number }[]
  }
}>()

const emit = defineEmits<{
  'batch-fill': [upper: string, lower: string]
  'copy-selected': []
  'paste-to-selected': []
  'clear-selected': []
  'filter-empty': []
  'export-template': []
  'export-config': [dimension: string]
  'export-diff-report': []
  'export-pdf': []
  'import-excel': []
  'toggle-panel': []
}>()

const isCollapsed = ref(true)
const activeTab = ref('batch-tools')

watch(() => props.expanded, (val) => {
  isCollapsed.value = val === false
}, { immediate: true })

function expandTo(tab: string) {
  activeTab.value = tab
  isCollapsed.value = false
}

const batchFill = ref({ upper: '', lower: '' })
const exportDimension = ref('bom')
const changeNote = ref('')
const dimensionKey = ref<'byProcess' | 'byStation' | 'byOwner'>('byProcess')

const dimensionRows = computed(() => {
  const ds = props.dimensionStats
  if (!ds) return []
  return ds[dimensionKey.value] || []
})

const stats = computed(() => {
  if (props.bomStats) return props.bomStats
  const fp = props.fillPercent
  const total = 100 // fallback
  const filled = Math.round(total * fp / 100)
  return { totalItems: 0, totalParams: total, filledCount: filled, emptyCount: total - filled }
})

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
  emit('toggle-panel')
}

function onTabChange(tab: string) {
  activeTab.value = tab
}

function handleBatchFill() {
  ElMessageBox.confirm('确认批量填充阈值？', '批量填充', { type: 'warning' })
    .then(() => {
      emit('batch-fill', batchFill.value.upper, batchFill.value.lower)
    })
    .catch(() => {})
}

function handleClearSelected() {
  ElMessageBox.confirm('确认清空选中参数？此操作不可撤销', '确认清空', { type: 'warning' })
    .then(() => emit('clear-selected'))
    .catch(() => {})
}

function handleCopyPrevProcess() {
  ElMessageBox.confirm('确认复制上工序全部参数到当前工序？', '跨工序复制', { type: 'warning' })
    .then(() => emit('copy-selected'))
    .catch(() => {})
}

function handleCopyPrevStation() {
  ElMessageBox.confirm('确认复制上工位参数？', '复制上工位', { type: 'warning' })
    .then(() => emit('paste-to-selected'))
    .catch(() => {})
}
</script>

<style scoped>
.tool-panel {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border-left: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease;
  overflow: hidden;
}

.tool-panel.collapsed {
  width: 40px;
}

.icon-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 8px 0;
  height: 100%;
  background: #fafafa;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  color: #606266;
  cursor: pointer;
}

.icon-btn:hover {
  background: #ecf5ff;
  color: #409eff;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 8px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-right: auto;
  padding-left: 4px;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.tab-content {
  padding: 8px 10px;
}

.section {
  margin-bottom: 4px;
}

.section-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 6px;
}

.fill-inputs {
  display: flex;
  gap: 6px;
}

.fill-inputs .el-input {
  flex: 1;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.stat-item {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 8px;
  text-align: center;
}

.stat-num {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.stat-num.success {
  color: #67c23a;
}

.stat-num.danger {
  color: #f56c6c;
}

.stat-label {
  display: block;
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

.w-full {
  width: 100%;
}

.mt-1 {
  margin-top: 4px;
}
</style>
