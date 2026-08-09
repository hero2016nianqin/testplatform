<template>
  <div>
    <el-table :data="registrations" v-loading="loading" style="width: 100%">
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="display_name" label="真实姓名" />
      <el-table-column prop="department" label="部门" />
      <el-table-column prop="requested_role" label="申请角色">
        <template #default="{ row }">
          {{ roleLabels[row.requested_role] || row.requested_role }}
        </template>
      </el-table-column>
      <el-table-column prop="requested_domains" label="申请领域">
        <template #default="{ row }">
          <span v-if="row.requested_domains?.length">
            {{ row.requested_domains.join(', ') }}
          </span>
          <span v-else class="text-gray-400">无</span>
        </template>
      </el-table-column>
      <el-table-column prop="justification" label="申请说明" />
      <el-table-column prop="created_at" label="创建时间" :formatter="formatTime" />
      <el-table-column prop="status" label="状态">
        <template #default="{ row }">
          <el-tag :type="statusTag[row.status] || 'info'">
            {{ statusLabels[row.status] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'pending'"
            type="primary"
            size="small"
            @click="approve(row)"
          >
            通过
          </el-button>
          <el-button
            v-if="row.status === 'pending'"
            type="danger"
            size="small"
            @click="reject(row)"
          >
            驳回
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Approve Dialog -->
    <el-dialog v-model="approveDialog.visible" title="审核通过" width="400px">
      <el-form :model="approveDialog.form" label-width="80px">
        <el-form-item label="分配领域">
          <el-checkbox-group v-model="approveDialog.form.domains">
            <el-checkbox
              v-for="domain in domainOptions"
              :key="domain.value"
              :label="domain.value"
              >{{ domain.label }}</el-checkbox>
          </el-checkbox-group>
          <div v-if="!needsDomains(approveDialog.current?.requested_role)" class="text-sm text-gray-400 mt-2">
            该角色无需绑定领域
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approveDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="approveDialog.submitting" @click="submitApprove">
          确认激活
        </el-button>
      </template>
    </el-dialog>

    <!-- Reject Dialog -->
    <el-dialog v-model="rejectDialog.visible" title="驳回申请" width="400px">
      <el-form :model="rejectDialog.form" label-width="80px">
        <el-form-item label="驳回理由" required>
          <el-input
            v-model="rejectDialog.form.comment"
            type="textarea"
            :rows="3"
            placeholder="请输入驳回理由"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialog.visible = false">取消</el-button>
        <el-button type="danger" :loading="rejectDialog.submitting" @click="submitReject">
          确认驳回
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api/auth'
import { formatTime } from '@/utils'

const loading = ref(false)
const registrations = ref([])

const roleLabels: Record<string, string> = {
  super_admin: '超级管理员',
  equipment_manager: '装备经理',
  equipment_test_manager: '装备测试经理',
  equipment_developer: '装备开发人员',
  developer: '装备开发人员',
  process: '生产工艺人员',
  operator: '生产操作人员',
  fd_developer: '功放开发',
  duxingqi_developer: '双解码开发',
  trx_developer: 'TRX开发',
  algorithm_developer: '算法开发',
  power_developer: '电源开发',
  board_software_developer: '单板软件开发',
  ict_developer: 'ICT开发',
  product_se: '产品SE',
}

const domainOptions = [
  { label: '功放', value: '功放' },
  { label: '双解码', value: '双解码' },
  { label: 'TRX', value: 'TRX' },
  { label: '算法', value: '算法' },
  { label: '电源', value: '电源' },
  { label: '单板软件', value: '单板软件' },
  { label: 'ICT', value: 'ICT' },
]

const statusLabels: Record<string, string> = {
  pending: '待审核',
  active: '已激活',
  rejected: '已驳回',
}

const statusTag: Record<string, string> = {
  pending: 'warning',
  active: 'success',
  rejected: 'danger',
}

const noDomainRoles: string[] = [] // 领域始终可选（可选非必选）

const approveDialog = reactive({
  visible: false,
  submitting: false,
  current: null as any,
  form: {
    domains: [] as string[],
  },
})

const rejectDialog = reactive({
  visible: false,
  submitting: false,
  current: null as any,
  form: {
    comment: '',
  },
})

function needsDomains(role?: string) {
  if (!role) return true
  return !noDomainRoles.includes(role)
}

function approve(reg: any) {
  approveDialog.current = reg
  approveDialog.form.domains = reg.requested_domains || []
  approveDialog.visible = true
}

function reject(reg: any) {
  rejectDialog.current = reg
  rejectDialog.form.comment = ''
  rejectDialog.visible = true
}

async function submitApprove() {
  if (!approveDialog.current) return
  approveDialog.submitting = true
  try {
    await authApi.approveRegistration(approveDialog.current.id, {
      approved_domains: approveDialog.form.domains,
    })
    ElMessage.success('账号审核通过')
    approveDialog.visible = false
    fetchRegistrations()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '操作失败')
  } finally {
    approveDialog.submitting = false
  }
}

async function submitReject() {
  if (!rejectDialog.current) return
  if (!rejectDialog.form.comment.trim()) {
    ElMessage.error('请输入驳回理由')
    return
  }
  rejectDialog.submitting = true
  try {
    await authApi.rejectRegistration(rejectDialog.current.id, {
      comment: rejectDialog.form.comment,
    })
    ElMessage.success('账号已驳回')
    rejectDialog.visible = false
    fetchRegistrations()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '操作失败')
  } finally {
    rejectDialog.submitting = false
  }
}

async function fetchRegistrations() {
  loading.value = true
  try {
    const res = await authApi.listRegistrations(1, 50)
    registrations.value = res.data?.items || []
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

fetchRegistrations()
</script>

<style scoped>
.text-gray-400 {
  color: #9ca3af;
}
</style>
