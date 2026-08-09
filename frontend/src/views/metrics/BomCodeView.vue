<template>
  <div class="min-w-0">
    <div class="flex items-center justify-between gap-3 mb-2">
      <div class="flex items-center gap-3 min-w-0">
        <el-button size="small" @click="goBack"><el-icon class="mr-1"><ArrowLeft /></el-icon>返回</el-button>
        <el-icon :size="26" color="var(--el-color-primary)"><Odometer /></el-icon>
        <div class="min-w-0">
          <h1 class="section-title !mb-0 !border-0 !pl-0 text-xl truncate">BOM 编码指标</h1>
          <div class="section-subtitle mt-0.5 truncate">{{ route.params.bomCode }}</div>
        </div>
      </div>
      <div class="flex items-center gap-3" v-if="activeTab === 'edit'">
        <div class="flex items-center gap-2">
          <span class="text-sm text-gray-500 whitespace-nowrap">版本</span>
<el-select :model-value="selectedVersionLabel" style="width:240px" placeholder="选择版本" @change="onVersionChange">
             <el-option v-for="v in versions" :key="v.id" :value="v.id">
               <div class="flex items-center justify-between gap-2">
                 <span class="font-bold">v{{ v.version }}</span>
                 <el-tag size="small" :type="versionTagType(v)">{{ versionTagText(v) }}</el-tag>
               </div>
             </el-option>
           </el-select>
        </div>
        <el-button type="primary" :disabled="!canNewIteration" @click="handleNewIteration">
          <el-icon class="mr-1"><DocumentAdd /></el-icon>新建版本
        </el-button>
      </div>
    </div>

    <el-tabs :model-value="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="BOM 详情编辑" name="edit">
        <router-view v-if="activeTab === 'edit'" />
      </el-tab-pane>
      <el-tab-pane label="领域责任人维护" name="domain">
        <router-view v-if="activeTab === 'domain'" />
      </el-tab-pane>
      <el-tab-pane label="版本统计" name="stats">
        <router-view v-if="activeTab === 'stats'" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Odometer, DocumentAdd } from '@element-plus/icons-vue'
import { metricsApi } from '@/api/metrics'

const route = useRoute()
const router = useRouter()

const bomCode = computed(() => String(route.params.bomCode || ''))
const currentConfigId = computed(() => Number(route.params.id || 0))
const selectedVersionLabel = computed(() => {
  const v = versions.value.find(x => x.id === currentConfigId.value)
  return v ? `v${v.version}-${versionTagText(v)}` : ''
})
const versions = ref<any[]>([])

const activeTab = computed(() => {
  if (route.name === 'BomCodeDomain') return 'domain'
  if (route.name === 'BomCodeStats') return 'stats'
  return 'edit'
})

function versionTagType(v: any) {
  if (v.archived) return 'info'
  if (v.review_status === 'approved') return 'success'
  if (v.review_status === 'pending') return 'warning'
  if (v.review_status === 'rejected') return 'danger'
  return 'primary'
}
function versionTagText(v: any) {
  if (v.archived) return '已归档'
  if (v.review_status === 'approved') return '已发布'
  if (v.review_status === 'pending') return '评审中'
  if (v.review_status === 'rejected') return '已驳回'
  return '未评审'
}

const canNewIteration = computed(() => {
  const v = versions.value.find(x => x.id === currentConfigId.value)
  return !!(v && (v.archived || v.review_status === 'approved'))
})

async function loadVersions() {
  if (!bomCode.value) return
  const res = await metricsApi.listBomConfigsByCode(bomCode.value)
  versions.value = res.data || []
  if (versions.value.length > 0 && currentConfigId.value === 0) {
    const latest = versions.value[0]
    router.replace({ name: 'BomCodeEdit', params: { bomCode: bomCode.value, id: latest.id } })
  }
}

function goBack() {
  router.push({ name: 'BomConfig' })
}

function onVersionChange(newId: number | string) {
  const target = Number(newId)
  if (!target || target === currentConfigId.value) return
  router.replace({ name: 'BomCodeEdit', params: { bomCode: bomCode.value, id: target } })
}

function onTabChange(name: string | number) {
   if (name === 'domain') {
     router.replace({ name: 'BomCodeDomain', params: { bomCode: bomCode.value } })
   } else if (name === 'stats') {
     router.replace({ name: 'BomCodeStats', params: { bomCode: bomCode.value } })
} else {
      const targetId = currentConfigId.value || (versions.value.length > 0 ? versions.value[0].id : 0)
      if (targetId) {
        router.replace({ name: 'BomCodeEdit', params: { bomCode: bomCode.value, id: targetId } })
      }
    }
 }

async function handleNewIteration() {
  const configId = currentConfigId.value
  const row = versions.value.find(x => x.id === configId)
  if (!row) return
  try {
    let hasNonClosed = false
    try {
      const checkRes = await metricsApi.checkBomVersion(bomCode.value, configId)
      hasNonClosed = checkRes.data?.has_non_closed || false
    } catch { /* pre-check unavailable */ }
    if (hasNonClosed) {
      ElMessageBox.alert('该BOM编码已存在未评审/未归档版本，不允许新建迭代', '无法新建迭代', {
        confirmButtonText: '确定', type: 'warning',
      })
      return
    }
    const label = row.archived ? '已归档' : '已发布'
    await ElMessageBox.confirm(
      `将基于当前${label}版本创建新迭代\n\nBOM编码: ${bomCode.value}\n当前版本: v${row.version}\n\n新版本将复制所有指标和参数数据，生成未评审的迭代版本继续编辑？`,
      '基于此版本新建',
    )
    const res = await metricsApi.createNewIteration(configId)
    const newId = res.data?.id
    await loadVersions()
    ElMessage.success('新迭代版本已创建')
    if (newId) {
      router.replace({ name: 'BomCodeEdit', params: { bomCode: bomCode.value, id: newId } })
    }
  } catch (e: any) {
    if (e?.response?.data?.message) {
      ElMessage.error(e.response.data.message)
    } else if (e?.message && e.message !== 'cancel' && e.message !== '取消') {
      ElMessage.error(e.message)
    }
  }
}

watch(bomCode, () => { loadVersions() }, { immediate: true })
</script>