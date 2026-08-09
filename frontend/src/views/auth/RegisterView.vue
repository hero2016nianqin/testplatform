<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="w-full max-w-md">
      <div class="bg-white rounded-lg shadow-lg p-8">
        <div class="text-center mb-6">
          <h1 class="text-2xl font-bold text-gray-800">账号自助注册</h1>
          <p class="text-sm text-gray-500 mt-1">申请后请等待管理员审核激活</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="80px"
        >
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" placeholder="英文字母+数字，6-20位" />
          </el-form-item>

          <el-form-item label="登录密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="≥8位，包含字母和数字"
            />
          </el-form-item>

          <el-form-item label="真实姓名" prop="display_name">
            <el-input v-model="form.display_name" placeholder="请输入真实姓名" />
          </el-form-item>

          <el-form-item label="所属部门" prop="department">
            <el-input v-model="form.department" placeholder="请输入部门名称" />
          </el-form-item>

          <el-form-item label="申请角色" prop="requested_role">
            <el-select v-model="form.requested_role" class="w-full" placeholder="请选择申请角色">
              <el-option
                v-for="role in roleOptions"
                :key="role.value"
                :label="role.label"
                :value="role.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="申请领域">
            <el-checkbox-group
              v-model="form.requested_domains"
              :disabled="!domainEditable"
              class="w-full"
            >
              <el-checkbox
                v-for="domain in domainOptions"
                :key="domain.value"
                :label="domain.value"
                :disabled="!domainEditable"
                >{{ domain.label }}</el-checkbox>            </el-checkbox-group>
            <div v-if="!domainEditable" class="text-sm text-gray-400 mt-1">
              该角色无需绑定领域
            </div>
          </el-form-item>

          <el-form-item label="申请说明" prop="justification">
            <el-input
              v-model="form.justification"
              type="textarea"
              :rows="3"
              placeholder="请输入工作范围等审核参考信息"
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              class="w-full"
              :loading="submitting"
              @click="onSubmit"
            >
              提交注册申请
            </el-button>
          </el-form-item>

          <div class="text-center mt-4">
            <router-link to="/login" class="text-sm text-primary hover:underline">
              已有账号？前往登录
            </router-link>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api/auth'

const router = useRouter()
const formRef = ref()
const submitting = ref(false)

const roleOptions = [
  { label: '装备开发人员', value: 'equipment_developer' },
  { label: '功放开发', value: 'fd_developer' },
  { label: '双解码开发', value: 'duxingqi_developer' },
  { label: 'TRX开发', value: 'trx_developer' },
  { label: '算法开发', value: 'algorithm_developer' },
  { label: '电源开发', value: 'power_developer' },
  { label: '单板软件开发', value: 'board_software_developer' },
  { label: 'ICT开发', value: 'ict_developer' },
  { label: '产品SE', value: 'product_se' },
  { label: '生产工艺人员', value: 'process' },
  { label: '生产操作人员', value: 'operator' },
  { label: '装备经理', value: 'equipment_manager' },
  { label: '装备测试经理', value: 'equipment_test_manager' },
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

const noDomainRoles = [
  'super_admin',
  'equipment_manager',
  'equipment_test_manager',
  'process',
  'operator',
]

const form = reactive({
  username: '',
  password: '',
  display_name: '',
  department: '',
  requested_role: '',
  requested_domains: [] as string[],
  justification: '',
})

const domainEditable = computed(() => {
  return !noDomainRoles.includes(form.requested_role)
})

watch(() => form.requested_role, (newRole) => {
  if (noDomainRoles.includes(newRole)) {
    form.requested_domains = []
  }
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[a-zA-Z][a-zA-Z0-9]{5,19}$/, message: '6-20位，以字母开头，仅含英文字母和数字', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { pattern: /^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z\d!@#$%^&*]{8,}$/, message: '至少8位，包含字母和数字', trigger: 'blur' },
  ],
  display_name: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
  department: [{ required: true, message: '请输入部门', trigger: 'blur' }],
  requested_role: [{ required: true, message: '请选择申请角色', trigger: 'change' }],
  justification: [{ required: true, message: '请输入申请说明', trigger: 'blur' }],
}

async function checkUsernameUnique() {
  if (!form.username) return
  try {
    const res = await authApi.listUsers(1, 1, undefined, undefined)
    const exists = res.data?.items?.some((u: any) => u.username === form.username)
    if (exists) {
      ElMessage.error('用户名已存在')
      return false
    }
    return true
  } catch {
    return true
  }
}

async function onSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate()
  if (!valid) return

  if (!(await checkUsernameUnique())) return

  submitting.value = true
  try {
    await authApi.register({
      username: form.username,
      display_name: form.display_name,
      password: form.password,
      department: form.department,
      requested_role: form.requested_role,
      requested_domains: form.requested_domains.length ? form.requested_domains : undefined,
      justification: form.justification,
    })
    ElMessage.success('注册成功，请等待管理员审核激活')
    await router.push('/login')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '注册失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.text-primary {
  color: #409EFF;
}
</style>
