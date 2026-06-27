<script setup lang="ts">
defineProps<{ title?: string; description?: string; icon?: string }>()
</script>

<template>
  <div class="lh-empty">
    <el-icon v-if="icon" :size="44"><component :is="icon" /></el-icon>
    <div style="font-size:15px;margin-top:8px;color:#1f2430;font-weight:500">{{ title || '暂无数据' }}</div>
    <div v-if="description" style="font-size:13px;margin-top:4px">{{ description }}</div>
  </div>
</template>