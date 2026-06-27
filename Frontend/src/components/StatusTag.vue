<script setup lang="ts">
import { computed } from 'vue'
import type { TaskItemStatus, TaskStatus } from '@/types'
import { TASK_ITEM_STATUS, TASK_STATUS } from '@/constants'
import { ElTag } from 'element-plus'

const props = defineProps<{ status: string }>()

const meta = computed(() => {
  if (props.status in TASK_ITEM_STATUS) {
    return TASK_ITEM_STATUS[props.status as TaskItemStatus]
  }
  if (props.status in TASK_STATUS) {
    return TASK_STATUS[props.status as TaskStatus]
  }
  return { label: props.status, type: 'info' as const }
})
</script>

<template>
  <ElTag :type="meta.type" effect="light" size="small">{{ meta.label }}</ElTag>
</template>