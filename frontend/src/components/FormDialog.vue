<template>
  <el-dialog
    :model-value="visible"
    :title="title"
    :width="width"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:visible', $event)"
    @open="$emit('open')"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      :label-width="labelWidth"
      v-bind="$attrs"
    >
      <slot :form="formData" />
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ submitText || '确定' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { FormInstance } from 'element-plus'

const props = withDefaults(defineProps<{
  visible: boolean
  title: string
  formData: Record<string, any>
  rules?: any
  submitting?: boolean
  submitText?: string
  width?: string
  labelWidth?: string
}>(), {
  width: '500px',
  labelWidth: '100px',
})

const emit = defineEmits<{
  'update:visible': [v: boolean]
  submit: []
  open: []
}>()

const formRef = ref<FormInstance>()

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  emit('submit')
}
</script>
