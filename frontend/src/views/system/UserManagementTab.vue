<template>
  <div>
    <div class="mb-4 flex justify-between items-center">
      <el-button type="primary" @click="addUser">新增用户</el-button>
      <div class="flex gap-2">
        <el-select v-model="filters.role" placeholder="筛选角色" clearable class="w-180px" @clear="fetchUsers" @change="fetchUsers">
          <el-option
            v-for="role in roleOptions"
            :key="role.value"
            :label="role.label"
            :value="role.value"
          />
        </el-select>
        <el-select v-model="filters.status" placeholder="筛选状态" clearable class="w-180px" @clear="fetchUsers" @change="fetchUsers">
          <el-option label="已激活" value="active" />
          <el-option label="已禁用" value="inactive" />
        </el-select>
      </div>
    </div>

    <el-table :data="users" v-loading="loading" style="width: 100%">
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="display_name" label="真实姓名" />
      <el-table-column prop="role" label="角色">
        <template #default="{ row }">
          {{ roleLabels[row.role] || row.role }}
        </template>
      </el-table-column>
      <el-table-column prop="domains" label="绑定领域">
        <template #default="{ row }">
          <span v-if="row.domains?.length">{{ row.domains.join(', ') }}</span>
          <span v-else class="text-gray-400">无</span>
        </template>
      </el-table-column>
      <el-table-column prop="department" label="部门" />
      <el-table-column prop="registration_status" label="状态">
        <template #default="{ row }">
          <el-tag :type="statusTag[row.registration_status === 'active' ? 'active' : 'inactive']">
            {{ userStatusLabel(row) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" :formatter="formatTime" />
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="editUser(row)">
            编辑
          </el-button>
          <el-button type="warning" size="small" @click="resetPassword(row)">
            重置密码
          </el-button>
          <el-button
            type="danger"
            size="small"
            :disabled="row.registration_status === 'pending'"
            @click="disableUser(row)"
          >
            禁用
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Edit User Dialog -->
    <el-dialog v-model="userDialog.visible" :title="userDialog.title" width="500px">
      <el-form :model="userDialog.form" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="userDialog.form.username" :disabled="!!userDialog.form.id" />
        </el-form-item>
        <el-form-item label="真实姓名">
          <el-input v-model="userDialog.form.display_name" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userDialog.form.role" class="w-full">
            <el-option
              v-for="role in roleOptions"
              :key="role.value"
              :label="role.label"
              :value="role.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="绑定领域">
          <el-checkbox-group v-model="userDialog.form.domains" :disabled="!domainEditable">
            <el-checkbox
              v-for="domain in domainOptions"
              :key="domain.value"
              :label="domain.value"
              >{{ domain.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="userDialog.form.department" />
        </el-form-item>
        <el-form-item label="初始密码" v-if="!userDialog.form.id">
          <el-input v-model="userDialog.form.password" type="password" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="userDialog.submitting" @click="saveUser">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- Reset Password Dialog -->
    <el-dialog v-model="resetPwdDialog.visible" title="重置密码" width="400px">
      <el-form :model="resetPwdDialog.form" label-width="80px">
        <el-form-item label="新密码" required>
          <el-input v-model="resetPwdDialog.form.password" type="password" autocomplete="new-password" />
        </el-form-item>
        <el-form-item label="确认密码" required>
          <el-input v-model="resetPwdDialog.form.confirmPassword" type="password" autocomplete="new-password" />
        </el-form-item>
        <div v-if="resetPwdDialog.error" class="text-red-500 text-sm mt-2">
          {{ resetPwdDialog.error }}
        </div>
      </el-form>
      <template #footer>
        <el-button @click="resetPwdDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="resetPwdDialog.submitting" @click="submitResetPassword">
          确认重置
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { authApi } from '@/api/auth'
import { formatTime } from '@/utils'

const loading = ref(false)
const users = ref([])

const roleOptions = [
  { label: '超级管理员', value: 'super_admin' },
  { label: '装备经理', value: 'equipment_manager' },
  { label: '装备测试经理', value: 'equipment_test_manager' },
  { label: '装备开发人员', value: 'equipment_developer' },
  { label: '生产工艺人员', value: 'process' },
  { label: '生产操作人员', value: 'operator' },
  { label: '功放开发', value: 'fd_developer' },
  { label: '双解码开发', value: 'duxingqi_developer' },
  { label: 'TRX开发', value: 'trx_developer' },
  { label: '算法开发', value: 'algorithm_developer' },
  { label: '电源开发', value: 'power_developer' },
  { label: '单板软件开发', value: 'board_software_developer' },
  { label: 'ICT开发', value: 'ict_developer' },
  { label: '产品SE', value: 'product_se' },
]

const domainOptions = [
  { label: '功放', value: '功放' },
  { label: '双解码', value: '双解码' },
  { label: 'TRX', value: 'TRX' },
  { label: '算法', value: '算法' },
  { label: '电源', value: '电源' },
  { label: '单板软件', value: '单板软件' },
  { label: 'ICT', value: 'ICT' },
]

const noDomainRoles = ['super_admin', 'equipment_manager', 'equipment_test_manager', 'process', 'operator']

const roleLabels: Record<string, string> = Object.fromEntries(roleOptions.map(r => [r.value, r.label]))

const statusTag: Record<string, string> = {
  active: 'success',
  inactive: 'danger',
}

const userStatusLabel = (row: any) => {
  if (row.registration_status === 'pending') return '待审核'
  if (row.is_active && row.registration_status === 'active') return '已激活'
  return '已禁用'
}

const filters = reactive({
  role: '',
  status: '',
})

const userDialog = reactive({
  visible: false,
  title: '',
  submitting: false,
  form: {} as any,
})

const domainEditable = computed(() => {
  return !noDomainRoles.includes(userDialog.form.role)
})

const resetPwdDialog = reactive({
  visible: false,
  submitting: false,
  currentUser: null as any,
  form: {
    password: '',
    confirmPassword: '',
  },
  error: '',
})

function addUser() {
  userDialog.form = {
    username: '',
    display_name: '',
    password: '',
    role: 'operator',
    domains: [],
    department: '',
  }
  userDialog.title = '新增用户'
  userDialog.visible = true
}

function editUser(row: any) {
  userDialog.form = { ...row, password: '' }
  userDialog.title = '编辑账号'
  userDialog.visible = true
}

async function saveUser() {
  userDialog.submitting = true
  try {
    if (userDialog.form.id) {
      await authApi.updateUser(userDialog.form.id, {
        display_name: userDialog.form.display_name,
        role: userDialog.form.role,
        domains: userDialog.form.domains,
        department: userDialog.form.department,
      })
    } else {
      await authApi.createUser({
        username: userDialog.form.username,
        display_name: userDialog.form.display_name,
        password: userDialog.form.password || '123456',
        role: userDialog.form.role,
        domains: userDialog.form.domains,
      })
    }
    ElMessage.success('保存成功')
    userDialog.visible = false
    fetchUsers()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '保存失败')
  } finally {
    userDialog.submitting = false
  }
}

function resetPassword(row: any) {
  resetPwdDialog.currentUser = row
  resetPwdDialog.form = { password: '', confirmPassword: '' }
  resetPwdDialog.error = ''
  resetPwdDialog.visible = true
}

async function submitResetPassword() {
  if (!resetPwdDialog.form.password) {
    resetPwdDialog.error = '请输入新密码'
    return
  }
  if (resetPwdDialog.form.password !== resetPwdDialog.form.confirmPassword) {
    resetPwdDialog.error = '两次输入密码不一致'
    return
  }
  if (resetPwdDialog.form.password.length < 8 || !/[a-zA-Z]/.test(resetPwdDialog.form.password) || !/\d/.test(resetPwdDialog.form.password)) {
    resetPwdDialog.error = '密码需≥8位，含字母和数字'
    return
  }
  resetPwdDialog.submitting = true
  try {
    await authApi.resetPassword(resetPwdDialog.currentUser.id, {
      new_password: resetPwdDialog.form.password,
    })
    ElMessage.success('密码重置成功')
    resetPwdDialog.visible = false
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '重置失败')
  } finally {
    resetPwdDialog.submitting = false
  }
}

async function disableUser(row: any) {
  try {
    await ElMessageBox.confirm(`确定禁用账号 ${row.username} 吗？`, '提示', {
      type: 'warning',
    })
    await authApi.deleteUser(row.id)
    ElMessage.success('账号已禁用')
    fetchUsers()
  } catch {
    // cancelled
  }
}

async function fetchUsers() {
  loading.value = true
  try {
    const res = await authApi.listUsers(1, 50, filters.role || undefined, filters.status || undefined)
    users.value = res.data?.items || []
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

fetchUsers()
</script>

<style scoped>
.text-gray-400 {
  color: #9ca3af;
}
.w-180px {
  width: 180px;
}
</style>
