<template>
  <el-menu
    :default-active="route.path"
    :collapse="appStore.sidebarCollapsed"
    :collapse-transition="false"
    class="h-screen overflow-y-auto border-r"
    background-color="#304156"
    text-color="#bfcbd9"
    active-text-color="#409EFF"
    router
    :style="{ width: appStore.sidebarCollapsed ? '64px' : '240px', flexShrink: 0 }"
  >
    <div class="h-14 flex items-center justify-center text-white border-b border-gray-700" style="font-weight:800;font-size:1.35rem;letter-spacing:0.5px;white-space:nowrap">
      <span v-if="!appStore.sidebarCollapsed">Test Platform</span>
      <el-icon v-else class="text-white"><Setting /></el-icon>
    </div>
    <template v-for="item in visibleMenu" :key="item.path">
      <el-sub-menu v-if="item.children?.length" :index="item.path">
        <template #title>
          <el-icon><component :is="item.meta?.icon" /></el-icon>
          <span style="font-weight:600;font-size:1.05rem">{{ item.meta?.title }}</span>
        </template>
        <el-menu-item
          v-for="child in visibleChildren(item)"
          :key="child.path"
          :index="`/${item.path}/${child.path}`"
        >
          <el-icon><component :is="child.meta?.icon" /></el-icon>
          <template #title>{{ child.meta?.title }}</template>
        </el-menu-item>
      </el-sub-menu>
      <el-menu-item v-else :index="'/' + item.path" style="font-weight:600;font-size:1.05rem;white-space:nowrap">
        <el-icon><component :is="item.meta?.icon" /></el-icon>
        <template #title>{{ item.meta?.title }}</template>
      </el-menu-item>
    </template>
  </el-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import router from '@/router'

const route = useRoute()
const authStore = useAuthStore()
const appStore = useAppStore()

const menuItems = computed(() =>
  router.options.routes
    .find((r) => r.path === '/')
    ?.children?.filter((r) => !r.meta?.hidden) || []
)

const visibleMenu = computed(() =>
  menuItems.value.filter((item) => {
    const roles = item.meta?.roles as string[] | undefined
    if (!roles) return true
    return roles.some((r) => authStore.hasRole(r))
  })
)

function visibleChildren(item: any) {
  const children = item.children?.filter((c: any) => !c.meta?.hidden) || []
  return children.filter((child: any) => {
    const roles = child.meta?.roles as string[] | undefined
    if (!roles) return true
    return roles.some((r) => authStore.hasRole(r))
  })
}
</script>
