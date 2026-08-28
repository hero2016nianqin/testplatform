import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/auth/register',
    name: 'Register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/components/AppLayout.vue'),
    meta: { requiresAuth: true },
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '仪表盘', icon: 'Monitor', roles: ['operator', 'process', 'developer', 'super_admin'] },
      },
      {
        path: 'equipment',
        name: 'Equipment',
        component: () => import('@/views/equipment/EquipmentView.vue'),
        meta: { title: '线体装备', icon: 'Setting', roles: ['operator', 'process', 'developer', 'super_admin'] },
      },
      {
        path: 'records',
        name: 'Records',
        component: () => import('@/views/records/RecordsView.vue'),
        meta: { title: '测试记录', icon: 'Document', roles: ['operator', 'process', 'developer', 'super_admin'] },
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('@/views/logs/LogsView.vue'),
        meta: { title: '日志查询', icon: 'Tickets', roles: ['operator', 'process', 'developer', 'super_admin'] },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/SettingsView.vue'),
        meta: { title: '全局配置', icon: 'Tools', roles: ['process', 'developer', 'super_admin'] },
      },
      {
        path: 'system/permission-admin',
        name: 'PermissionAdmin',
        component: () => import('@/views/system/PermissionAdminView.vue'),
        meta: { title: '权限管理', icon: 'User', roles: ['super_admin'], requiresAuth: true },
      },
      {
        path: 'station/:id',
        name: 'StationMonitor',
        component: () => import('@/views/station/StationMonitorView.vue'),
        meta: { title: '测试执行', roles: ['operator', 'process', 'developer', 'super_admin'], hidden: true },
      },
      {
        path: 'station-settings/:id',
        name: 'StationSettings',
        component: () => import('@/views/station/StationSettingsView.vue'),
        meta: { title: '单站配置', icon: 'Setting', roles: ['process', 'developer', 'super_admin'], hidden: true },
      },
      {
        path: 'releases',
        name: 'Releases',
        component: () => import('@/views/releases/ReleasesView.vue'),
        meta: { title: '版本管理', icon: 'Upload', roles: ['operator', 'process', 'developer', 'super_admin'] },
      },
      {
        path: 'releases/:id',
        name: 'VersionDetail',
        component: () => import('@/views/releases/VersionDetailView.vue'),
        meta: { title: '版本详情', roles: ['operator', 'process', 'developer', 'super_admin'], hidden: true },
      },
      {
        path: 'init',
        name: 'Init',
        component: () => import('@/views/init/InitView.vue'),
        meta: { title: '系统初始化', icon: 'Warning', roles: ['developer', 'super_admin'] },
      },
      {
        path: 'metrics',
        redirect: '/metrics/bom-config',
        meta: { title: '指标管理系统', icon: 'DataBoard', roles: ['process', 'developer', 'super_admin'] },
        children: [
          {
            path: 'bom-config',
            name: 'BomConfig',
            component: () => import('@/views/metrics/BomConfigView.vue'),
            meta: { title: 'BOM指标配置', icon: 'Odometer' },
          },
          {
            path: 'bom-config/:id/edit',
            name: 'BomDetail',
            component: () => import('@/views/metrics/BomDetailView.vue'),
            meta: { title: 'BOM详情编辑', roles: ['process', 'developer', 'super_admin'], hidden: true },
          },
          {
            path: 'bom-config/:bomCode/code',
            name: 'BomCode',
            component: () => import('@/views/metrics/BomCodeView.vue'),
            meta: { title: 'BOM编码指标', roles: ['process', 'developer', 'super_admin'], hidden: true },
            children: [
              {
                path: 'edit/:id',
                name: 'BomCodeEdit',
                component: () => import('@/views/metrics/BomDetailView.vue'),
                meta: { title: 'BOM详情编辑', roles: ['process', 'developer', 'super_admin'], hidden: true },
              },
              {
                path: 'domain',
                name: 'BomCodeDomain',
                component: () => import('@/views/metrics/BomDomainOwnerView.vue'),
                meta: { title: '领域责任人维护', roles: ['process', 'developer', 'super_admin'], hidden: true },
              },
              {
                path: 'stats',
                name: 'BomCodeStats',
                component: () => import('@/views/metrics/BomVersionStatsView.vue'),
                meta: { title: '版本统计', roles: ['process', 'developer', 'super_admin'], hidden: true },
              },
            ],
          },
          {
            path: 'collections',
            name: 'MetricsCollections',
            component: () => import('@/views/metrics/CollectionView.vue'),
            meta: { title: '测试项集合管理', icon: 'Collection' },
          },
          {
            path: 'dictionary',
            name: 'MetricsDictionary',
            component: () => import('@/views/metrics/DictionaryView.vue'),
            meta: { title: '指标字典库', icon: 'Files' },
          },
          {
            path: 'versions',
            name: 'MetricsVersions',
            component: () => import('@/views/metrics/VersionHistoryView.vue'),
            meta: { title: '指标版本记录', icon: 'Timer' },
          },
          {
            path: 'query-export',
            name: 'MetricsQueryExport',
            component: () => import('@/views/metrics/QueryExportView.vue'),
            meta: { title: '指标查询导出', icon: 'Download' },
          },
          {
            path: 'scripts',
            name: 'MetricsScripts',
            component: () => import('@/views/metrics/ScriptTemplateView.vue'),
            meta: { title: '自定义脚本模板', icon: 'Code' },
          },
          {
            path: 'alerts',
            name: 'MetricsAlerts',
            component: () => import('@/views/metrics/AlertCenterView.vue'),
            meta: { title: '指标告警中心', icon: 'WarningFilled' },
          },
        ],
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  if (!authStore.isLoggedIn && to.meta.requiresAuth !== false) {
    await authStore.fetchCurrentUser()
    if (!authStore.isLoggedIn) {
      next('/login')
      return
    }
  }

  if (to.name === 'Login' && authStore.isLoggedIn) {
    next('/')
    return
  }

  const requiredRoles = to.meta?.roles as string[] | undefined
  if (requiredRoles && authStore.isLoggedIn) {
    const hasAccess = requiredRoles.some((r) => authStore.hasRole(r))
    if (!hasAccess) {
      next('/dashboard')
      return
    }
  }

  next()
})

export default router
