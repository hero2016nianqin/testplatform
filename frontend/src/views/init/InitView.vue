<template>
  <div>
    <div class="flex items-center gap-2 mb-6">
      <el-icon :size="26" color="var(--el-color-primary)"><SetUp /></el-icon>
      <div>
        <h1 class="section-title !mb-0 !border-0 !pl-0 text-xl">系统初始化</h1>
        <div class="section-subtitle mt-0.5">工厂 / 线体 / 工站基础数据</div>
      </div>
    </div>
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="hover" class="app-card-hover">
          <template #header><span class="font-bold">初始化系统</span></template>
          <p class="text-gray-500 mb-4">创建默认用户、厂区、线体、装备、测试模板等种子数据</p>
          <el-button type="primary" @click="handleInit" :loading="initLoading">
            <el-icon class="mr-1"><SetUp /></el-icon>执行初始化
          </el-button>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover" class="app-card-hover">
          <template #header><span class="font-bold text-red-500">重置系统</span></template>
          <p class="text-gray-500 mb-4">清空所有数据并重建数据库（不可恢复）</p>
          <el-button type="danger" @click="handleReset" :loading="resetLoading">
            <el-icon class="mr-1"><Delete /></el-icon>执行重置
          </el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api/index'

const initLoading = ref(false)
const resetLoading = ref(false)

async function handleInit() {
  initLoading.value = true
  try {
    await api.post('/init')
    ElMessage.success('系统初始化成功')
  } finally {
    initLoading.value = false
  }
}

async function handleReset() {
  try {
    await ElMessageBox.confirm('确定要重置系统吗？所有数据将丢失！', '警告', {
      confirmButtonText: '确认重置',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  resetLoading.value = true
  try {
    await api.post('/init/reset')
    ElMessage.success('系统已重置')
  } finally {
    resetLoading.value = false
  }
}
</script>
