<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listTasks, deleteTask, publishTask } from '@/api'
import type { Task } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import EmptyState from '@/components/EmptyState.vue'
import { formatDate } from '@/utils'

const router = useRouter()
const list = ref<Task[]>([])
const loading = ref(false)
const keyword = ref('')
const statusFilter = ref('')

async function load() {
  loading.value = true
  try {
    list.value = await listTasks({ status: statusFilter.value || undefined, keyword: keyword.value || undefined })
  } finally {
    loading.value = false
  }
}

function create() { router.push('/tasks/new') }
function detail(row: Task) { router.push(`/tasks/${row.id}`) }
function edit(row: Task) { router.push(`/tasks/${row.id}/edit`) }

async function publish(row: Task) {
  await ElMessageBox.confirm(`发布任务「${row.name}」？发布后将生成标注项。`, '发布', { type: 'warning' })
  await publishTask(row.id)
  ElMessage.success('已发布')
  load()
}

async function remove(row: Task) {
  await ElMessageBox.confirm(`删除任务「${row.name}」？`, '删除', { type: 'error' })
  await deleteTask(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <PageHeader title="任务管理" subtitle="创建并管理标注任务" />
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;margin-bottom:12px">
        <div style="display:flex;gap:8px">
          <el-input v-model="keyword" placeholder="搜索任务" clearable style="width:220px" @keyup.enter="load" />
          <el-select v-model="statusFilter" placeholder="状态" clearable style="width:140px" @change="load">
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="published" />
            <el-option label="已暂停" value="paused" />
            <el-option label="已完成" value="completed" />
            <el-option label="已归档" value="archived" />
          </el-select>
          <el-button @click="load">查询</el-button>
        </div>
        <el-button type="primary" @click="create">新建任务</el-button>
      </div>
      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="任务名称" min-width="180" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="100"><template #default="{ row }"><StatusTag :status="row.status" /></template></el-table-column>
        <el-table-column label="模板" width="140"><template #default="{ row }">{{ row.template?.name || row.template_id || '-' }}</template></el-table-column>
        <el-table-column label="AI审核" width="90"><template #default="{ row }"><el-tag size="small" :type="row.enable_ai_audit ? 'success':'info'" effect="plain">{{ row.enable_ai_audit ? '开启':'关闭' }}</el-tag></template></el-table-column>
        <el-table-column label="AI建议" width="90"><template #default="{ row }"><el-tag size="small" :type="row.enable_ai_suggestion ? 'success':'info'" effect="plain">{{ row.enable_ai_suggestion ? '开启':'关闭' }}</el-tag></template></el-table-column>
        <el-table-column label="创建时间" width="160"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="detail(row)">详情</el-button>
            <el-button size="small" link type="primary" @click="edit(row)">编辑</el-button>
            <el-button v-if="row.status==='draft'" size="small" link type="success" @click="publish(row)">发布</el-button>
            <el-button size="small" link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><EmptyState icon="List" description="暂无任务" /></template>
      </el-table>
    </el-card>
  </div>
</template>