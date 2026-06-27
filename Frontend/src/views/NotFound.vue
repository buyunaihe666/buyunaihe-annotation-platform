<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <div class="notfound">
    <h1>404</h1>
    <p>页面不存在</p>
    <el-button type="primary" @click="router.replace('/')">回到首页</el-button>
  </div>
</template>

<style scoped>
.notfound { min-height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:12px; background:#f5f7fb; }
.notfound h1 { font-size: 80px; margin:0; color:#4a6cf7; }
.notfound p { color:#8a93a6; }
</style>