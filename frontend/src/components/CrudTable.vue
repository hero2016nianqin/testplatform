<template>
  <div>
    <div v-if="$slots.header" class="flex items-center justify-between mb-3">
      <slot name="header" />
    </div>

    <el-table :data="data" v-bind="$attrs" stripe border v-loading="loading" style="width: 100%">
      <el-table-column v-if="showIndex" type="index" label="#" width="50" />
      <slot />
      <el-table-column v-if="showActions" label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <slot name="actions" :row="row">
            <el-button size="small" @click="$emit('edit', row)">编辑</el-button>
            <el-button size="small" type="danger" @click="$emit('delete', row)">删除</el-button>
          </slot>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="hasPagination" class="flex justify-end mt-3">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="safePageSize"
        :total="safeTotal"
        layout="total, prev, pager, next"
        @current-change="onPageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

defineOptions({ inheritAttrs: false })
const props = defineProps<{
  data: any[]
  loading?: boolean
  total?: number
  pageSize?: number
  showIndex?: boolean
  showActions?: boolean
}>()

const emit = defineEmits<{
  edit: [row: any]
  delete: [row: any]
  pageChange: [page: number]
}>()

const currentPage = defineModel<number>('currentPage', { default: 1 })

const safeTotal = computed(() => props.total || 0)
const safePageSize = computed(() => props.pageSize || 20)
const hasPagination = computed(() => safeTotal.value > safePageSize.value)

function onPageChange(page: number) {
  currentPage.value = page
  emit('pageChange', page)
}
</script>
