<template>
  <div class="min-w-0">
    <el-card shadow="hover" class="app-card-hover">
      <template #header>
        <div class="flex items-center justify-end">
          <el-button size="small" :loading="saving" type="primary" @click="save">
            <el-icon class="mr-1"><Check /></el-icon>保存配置
          </el-button>
        </div>
      </template>

      <div class="text-sm text-gray-500 mb-2">
        针对当前 BOM 编码（所有版本共享），配置「领域 → 负责人」映射关系。负责人仅作业务归属标签，不影响编辑权限。
      </div>

       <el-table :data="rows" v-loading="loading" stripe size="small" style="width:100%">
         <el-table-column type="index" label="#" width="50" />
         <el-table-column label="领域" min-width="200">
           <template #default="{ row }">
             <el-input v-model="row.domain" placeholder="领域名称（支持自定义输入）" clearable :disabled="row._source !== 'custom'" />
           </template>
         </el-table-column>
          <el-table-column label="负责人" min-width="220">
            <template #default="{ row }">
              <el-input v-model="row.owner" placeholder="输入负责人（账号/姓名，多人用逗号分隔）" clearable />
            </template>
          </el-table-column>
         <el-table-column label="来源" width="160">
           <template #default="{ row }">
             <el-tag v-if="row._source === 'saved'" size="small" type="success">已配置</el-tag>
             <el-tag v-else-if="row._source === 'collected'" size="small" type="warning">BOM已存在</el-tag>
             <el-tag v-else size="small" type="info">内置默认</el-tag>
           </template>
         </el-table-column>
         <el-table-column label="操作" width="80">
           <template #default="{ row }">
              <el-button v-if="row._source === 'custom'" size="small" type="danger" link @click="removeRow(rows.indexOf(row))">删除</el-button>
           </template>
         </el-table-column>
        <template #empty>
          <el-empty description="暂无领域，可点击下方按钮添加" :image-size="50" />
        </template>
      </el-table>

      <div class="mt-3">
        <el-button size="small" @click="addRow"><el-icon class="mr-1"><Plus /></el-icon>添加领域</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, Plus } from '@element-plus/icons-vue'
import { metricsApi } from '@/api/metrics'

const route = useRoute()
const bomCode = computed(() => String(route.params.bomCode || ''))

const loading = ref(false)
const saving = ref(false)
const rows = ref<any[]>([])
const defaults = ref<string[]>([])

function buildRows(ownerMap: Record<string, string>, collected: string[]) {
  const merged: string[] = []
  const push = (d: string) => {
    const key = String(d || '').trim()
    if (key && !merged.includes(key)) merged.push(key)
  }
  defaults.value.forEach(push)
  ;(collected || []).forEach(push)
  Object.keys(ownerMap || {}).forEach(push)
  rows.value = merged.map(d => ({
    domain: d,
    owner: (ownerMap?.[d] || ''),
    _source: ownerMap?.[d] ? 'saved' : (collected || []).includes(d) ? 'collected' : 'default',
  }))
}

async function load() {
  if (!bomCode.value) return
  loading.value = true
  try {
    const [ownersRes, domainsRes] = await Promise.all([
      metricsApi.getBomDomainOwnersByBomCode(bomCode.value),
      metricsApi.listIndicatorDomains().catch(() => ({ data: { defaults: [] as string[] } })),
    ])
    defaults.value = domainsRes.data?.defaults || []
    buildRows(ownersRes.data?.domain_owners || {}, ownersRes.data?.domains || [])
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e?.response?.data?.message || e?.message || ''))
  } finally {
    loading.value = false
  }
}

function addRow() {
  rows.value.push({ domain: '', owner: '', _source: 'custom' })
}

function removeRow(index: number) {
  rows.value.splice(index, 1)
}

async function save() {
  const domainOwners: Record<string, string> = {}
  let hasBlank = false
  for (const r of rows.value) {
    const d = String(r.domain || '').trim()
    if (!d) { hasBlank = true; continue }
    if (String(r.owner || '').trim()) domainOwners[d] = String(r.owner).trim()
  }
  if (hasBlank) {
    ElMessage.warning('存在未填写领域名称的行，已忽略')
  }
  saving.value = true
  try {
    await metricsApi.updateBomDomainOwnersByBomCode(bomCode.value, { domain_owners: domainOwners })
    ElMessage.success('领域负责人配置已保存')
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

watch(bomCode, () => { load() }, { immediate: true })
</script>