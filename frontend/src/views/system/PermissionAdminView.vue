<template>
  <div class="p-6">
    <div class="mb-4">
      <h2 class="text-xl font-bold">权限管理</h2>
      <p class="text-sm text-gray-500">管理用户账号审核与权限配置</p>
    </div>

    <el-tabs v-model="activeTab" class="permission-admin-tabs">
      <el-tab-pane name="registrations" label="注册申请审核" />
      <el-tab-pane name="users" label="账号管理" />
    </el-tabs>

    <div class="mt-4">
      <component :is="currentTabComponent" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineAsyncComponent } from 'vue'

const activeTab = ref('registrations')

const RegistrationAuditTab = defineAsyncComponent(() => import('./RegistrationAuditTab.vue'))
const UserManagementTab = defineAsyncComponent(() => import('./UserManagementTab.vue'))

const currentTabComponent = computed(() => {
  return activeTab.value === 'registrations' ? RegistrationAuditTab : UserManagementTab
})
</script>

<style>
.permission-admin-tabs .el-tabs__nav {
  font-weight: 600;
}
</style>
