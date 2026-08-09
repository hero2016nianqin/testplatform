<template>
  <el-container class="h-screen" style="display: flex; flex-direction: row; min-width: 0;">
    <NavSidebar />
    <el-container style="flex: 1; min-width: 0; display: flex; flex-direction: column;">
      <el-header class="bg-white shadow-sm flex items-center justify-between px-6" style="height: 50px; flex-shrink: 0; min-width: 0;">
        <div class="flex items-center gap-2 min-w-0">
          <el-icon class="cursor-pointer text-lg flex-shrink-0" @click="appStore.toggleSidebar">
            <Fold />
          </el-icon>
          <el-breadcrumb separator="/" class="min-w-0">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta?.title">{{ route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="flex items-center gap-4 flex-shrink-0">
          <el-tag v-if="appStore.wsConnected" type="success" size="small">WS 已连接</el-tag>
          <el-tag v-else type="danger" size="small">WS 断开</el-tag>
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="cursor-pointer text-sm flex items-center gap-1">
              <el-icon><User /></el-icon>
              {{ authStore.user?.display_name || authStore.user?.username }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><InfoFilled /></el-icon>个人信息
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="bg-gray-50 p-6 overflow-auto" style="flex: 1; min-width: 0; min-height: 0;">
        <router-view v-slot="{ Component }">
          <keep-alive include="StationMonitorView,StationSettingsView" :max="3">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'
import NavSidebar from './NavSidebar.vue'

const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()

function handleCommand(cmd: string) {
  if (cmd === 'logout') {
    authStore.logout()
    ElMessage.success('已退出登录')
  }
}
</script>
