<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listReviewTasks } from '@/api'
import type { Task } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { formatDate } from '@/utils'

const router = useRouter()
const list = ref<Task[]>([])
const loading = ref(false)
const keyword = ref('')

async function load() {
  loading.value = true
  try {
    list.value = await listReviewTasks({ keyword: keyword.value || undefined })
  } finally {
    loading.value = false
  }
}

function enter(task: Task) {
  router.push(`/review/items/${task.id}`)
}

onMounted(load)
</script>

<template>
  <div class="page">
    <PageHeader title="审核任务" subtitle="我负责审核的标注任务列表" />
    <el-card shadow="never">
      <div style="margin-bottom:12px">
        <el-input v-model="keyword" placeholder="搜索任务" clearable style="width:280px" @keyup.enter="load">
          <template #append><el-button @click="load">搜索</el-button></template>
        </el-input>
      </div>
      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="任务名称" min-width="200" />
        <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
        <el-table-column label="创建时间" width="170"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }"><el-button size="small" type="primary" link @click="enter(row)">进入审核</el-button></template>
        </el-table-column>
        <template #empty><EmptyState icon="Connection" description="暂无待审核任务" /></template>
      </el-table>
    </el-card>
  </div>
</template>