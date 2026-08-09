<template>
  <div class="min-w-0">
    <div class="flex items-center gap-2 mb-6">
      <el-icon :size="26" color="var(--el-color-primary)"><Code /></el-icon>
      <div>
        <h1 class="section-title !mb-0 !border-0 !pl-0 text-xl">自定义脚本模板管理</h1>
        <div class="section-subtitle mt-0.5">管理指标导出自定义 Python 脚本，支持在线编辑、语法校验、启用/禁用</div>
      </div>
    </div>

    <el-card shadow="hover" class="mb-4 app-card-hover">
      <el-form :inline="true" :model="query" @keyup.enter="search">
        <el-form-item label="搜索">
          <el-input v-model="query.keyword" placeholder="脚本名称" clearable style="width:240px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width:120px">
            <el-option label="启用" :value="1" />
            <el-option label="禁用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search"><el-icon class="mr-1"><Search /></el-icon>搜索</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="hover" class="app-card-hover">
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-bold">脚本模板列表</span>
          <el-button type="primary" size="small" @click="openCreateDialog()">
            <el-icon class="mr-1"><Plus /></el-icon>新建脚本
          </el-button>
        </div>
      </template>
      <el-table :data="list" stripe v-loading="loading" style="width:100%">
        <el-table-column prop="name" label="脚本名称" width="180" />
        <el-table-column prop="description" label="用途说明" show-overflow-tooltip />
        <el-table-column prop="output_format" label="输出格式" width="100">
          <template #default="{ row }">
            <el-tag :type="row.output_format === 'json' ? 'primary' : 'success'" size="small">{{ row.output_format.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-switch
              :model-value="row.status === 1"
              size="small"
              @change="(val: boolean) => handleToggleStatus(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="updated_by" label="更新人" width="100" />
        <el-table-column label="更新时间" width="160">
          <template #default="{ row }">{{ row.updated_at?.slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
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

    <FormDialog
      v-model:visible="formDialog.visible"
      :title="formDialog.isEdit ? '编辑脚本模板' : '新建脚本模板'"
      width="900px"
      :form-data="form"
      :rules="rules"
      :submitting="submitting"
      @submit="submitForm"
    >
      <template #default="{ form: f }">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="脚本名称" prop="name">
              <el-input v-model="f.name" placeholder="唯一名称，如：export_json" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="输出格式" prop="output_format">
              <el-select v-model="f.output_format" class="w-full">
                <el-option label="JSON" value="json" />
                <el-option label="INI" value="ini" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="用途说明" prop="description">
          <el-input v-model="f.description" placeholder="描述脚本用途、输出内容等" />
        </el-form-item>
        <el-form-item label="Python 脚本" prop="source_code">
          <div class="w-full border rounded overflow-hidden" :class="{ 'border-red-500': codeError }">
            <div class="flex items-center justify-between bg-gray-50 px-3 py-1.5 border-b text-xs text-gray-500">
              <span>indicator_data 为入参，result 为返回值</span>
              <div class="flex items-center gap-2">
                <el-tag v-if="codeValid === true" size="small" type="success">语法正确</el-tag>
                <el-tag v-else-if="codeValid === false" size="small" type="danger">语法错误</el-tag>
                <el-button size="small" type="primary" link :loading="validating" @click="validateCode">语法校验</el-button>
              </div>
            </div>
            <codemirror
              v-model="f.source_code"
              style="min-height:360px;border:none"
              :extensions="extensions"
              :disabled="false"
              @change="onCodeChange"
            />
          </div>
          <div v-if="codeError" class="text-red-500 text-xs mt-1 flex items-center gap-2">
            <el-icon><WarningFilled /></el-icon>
            <span>{{ codeError }}</span>
          </div>
        </el-form-item>
      </template>
    </FormDialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, shallowRef } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { WarningFilled } from '@element-plus/icons-vue'
import { metricsApi } from '@/api/metrics'

// CodeMirror
import { Codemirror } from 'vue-codemirror'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorView } from 'codemirror'

const extensions = shallowRef([
  python(),
  oneDark,
  EditorView.lineWrapping,
])

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const query = reactive({ keyword: '', status: undefined as number | undefined })
function search() { page.value = 1; load() }
function reset() { query.keyword = ''; query.status = undefined; page.value = 1; load() }

async function load() {
  loading.value = true
  try {
    const res = await metricsApi.listScriptTemplates({
      page: page.value,
      page_size: pageSize.value,
      keyword: query.keyword,
      status: query.status,
    })
    list.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

// ── Code syntax validation ──
const codeError = ref('')
const codeValid = ref<boolean | null>(null)
const validating = ref(false)

async function validateCode() {
  if (!form.source_code.trim()) {
    codeError.value = '代码为空'
    codeValid.value = false
    return
  }
  validating.value = true
  try {
    const res = await metricsApi.validateScriptSource({ source_code: form.source_code })
    const result = res.data
    if (result?.valid) {
      codeError.value = ''
      codeValid.value = true
      ElMessage.success('Python 语法正确')
    } else {
      codeError.value = result?.message || '语法错误'
      codeValid.value = false
    }
  } catch (e: any) {
    codeError.value = '校验请求失败'
    codeValid.value = false
  } finally {
    validating.value = false
  }
}

function onCodeChange(val: string) {
  codeValid.value = null
  codeError.value = ''
}

// ── Form Dialog ──
const submitting = ref(false)
const formDialog = reactive({ visible: false, isEdit: false, editId: 0 })
const form = reactive({
  name: '',
  description: '',
  source_code: '',
  output_format: 'json',
})
const rules = {
  name: [{ required: true, message: '请输入脚本名称', trigger: 'blur' }],
  source_code: [{ required: true, message: '请输入 Python 脚本代码', trigger: 'blur' }],
  output_format: [{ required: true, message: '请选择输出格式', trigger: 'change' }],
}

function openCreateDialog() {
  formDialog.isEdit = false
  formDialog.editId = 0
  Object.assign(form, { name: '', description: '', source_code: '', output_format: 'json' })
  codeError.value = ''
  codeValid.value = null
  formDialog.visible = true
}

function openEditDialog(row: any) {
  formDialog.isEdit = true
  formDialog.editId = row.id
  Object.assign(form, {
    name: row.name,
    description: row.description,
    source_code: row.source_code,
    output_format: row.output_format,
  })
  codeError.value = ''
  codeValid.value = null
  formDialog.visible = true
}

async function submitForm() {
  if (codeValid.value === false) {
    ElMessage.warning('请先修复代码语法错误')
    return
  }
  submitting.value = true
  try {
    if (formDialog.isEdit) {
      await metricsApi.updateScriptTemplate(formDialog.editId, { ...form })
      ElMessage.success('脚本模板更新成功')
    } else {
      await metricsApi.createScriptTemplate({ ...form })
      ElMessage.success('脚本模板创建成功')
    }
    formDialog.visible = false
    await load()
  } finally {
    submitting.value = false
  }
}

async function handleToggleStatus(row: any, val: boolean) {
  await metricsApi.toggleScriptStatus(row.id, val ? 1 : 0)
  ElMessage.success(`脚本已${val ? '启用' : '禁用'}`)
  await load()
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除脚本模板 "${row.name}"？`, '确认')
  await metricsApi.deleteScriptTemplate(row.id)
  ElMessage.success('脚本模板已删除')
  await load()
}

onMounted(load)
</script>
