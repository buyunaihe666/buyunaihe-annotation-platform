<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <div class="page-header">
    <h2>{{ title }}</h2>
    <div v-if="subtitle" class="sub">{{ subtitle }}</div>
  </div>
</template>