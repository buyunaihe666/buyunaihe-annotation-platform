<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listExports, listTasks } from '@/api'
import type { ExportRecord, Task } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { formatDate, formatSize } from '@/utils'

const records = ref<ExportRecord[]>([])
const tasks = ref<Task[]>([])
const loading = ref(false)
const taskFilter = ref<number | undefined>(undefined)

async function load() {
  loading.value = true
  try {
    records.value = await listExports(taskFilter.value)
  } finally {
    loading.value = false
  }
}

function downloadUrl(recId: number) {
  return `/api/export/${recId}/download`
}

function taskName(tid?: number) {
  const t = tasks.value.find(x => x.id === tid)
  return t ? t.name : tid
}

onMounted(async () => {
  tasks.value = await listTasks()
  await load()
})
</script>

<template>
  <div class="page">
    <PageHeader title="导出记录" subtitle="所有任务导出文件下载" />
    <el-card shadow="never">
      <div style="margin-bottom:12px">
        <el-select v-model="taskFilter" placeholder="按任务筛选" clearable style="width:280px" @change="load">
          <el-option v-for="t in tasks" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
        <el-button style="margin-left:8px" @click="load">刷新</el-button>
      </div>
      <el-table :data="records" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="任务" min-width="180"><template #default="{ row }">{{ taskName(row.task_id) }}</template></el-table-column>
        <el-table-column prop="format" label="格式" width="100" />
        <el-table-column prop="total" label="条数" width="90" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column label="创建时间" width="170"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
        <el-table-column label="完成时间" width="170"><template #default="{ row }">{{ formatDate(row.completed_at) }}</template></el-table-column>
        <el-table-column label="文件" min-width="240">
          <template #default="{ row }">
            <div v-if="row.files?.length">
              <a v-for="f in row.files" :key="f.id" :href="downloadUrl(row.id)" target="_blank" style="margin-right:10px;color:#4a6cf7">
                {{ f.filename }} ({{ formatSize(f.size) }})
              </a>
            </div>
            <span v-else style="color:#a0a6b5">—</span>
          </template>
        </el-table-column>
        <template #empty><EmptyState icon="Download" description="暂无导出记录" /></template>
      </el-table>
    </el-card>
  </div>
</template>