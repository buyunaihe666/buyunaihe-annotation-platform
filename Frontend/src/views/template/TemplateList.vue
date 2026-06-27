<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listTemplates, deleteTemplate, publishTemplate, archiveTemplate } from '@/api'
import type { Template } from '@/types'
import { TASK_STATUS } from '@/constants'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import EmptyState from '@/components/EmptyState.vue'
import { formatDate } from '@/utils'

const router = useRouter()
const list = ref<Template[]>([])
const loading = ref(false)
const keyword = ref('')

async function load() {
  loading.value = true
  try {
    list.value = await listTemplates({ keyword: keyword.value || undefined })
  } finally {
    loading.value = false
  }
}

function create() { router.push('/templates/new') }
function edit(row: Template) { router.push(`/templates/${row.id}/edit`) }
function preview(row: Template) { router.push(`/templates/${row.id}/preview`) }

async function publish(row: Template) {
  await ElMessageBox.confirm(`确认发布模板「${row.name}」吗？发布后可用于任务绑定。`, '发布', { type: 'warning' })
  await publishTemplate(row.id)
  ElMessage.success('已发布')
  load()
}

async function archive(row: Template) {
  await ElMessageBox.confirm(`归档模板「${row.name}」？`, '归档', { type: 'warning' })
  await archiveTemplate(row.id)
  ElMessage.success('已归档')
  load()
}

async function remove(row: Template) {
  await ElMessageBox.confirm(`删除模板「${row.name}」？此操作不可恢复。`, '删除', { type: 'error' })
  await deleteTemplate(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <PageHeader title="标注模板" subtitle="配置数据标注的字段与样表模板" />
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;margin-bottom:12px">
        <el-input v-model="keyword" placeholder="搜索模板名称" clearable style="width:260px" @clear="load" @keyup.enter="load">
          <template #append><el-button @click="load">搜索</el-button></template>
        </el-input>
        <el-button type="primary" @click="create">新建模板</el-button>
      </div>
      <el-table :data="list" v-loading="loading" border stripe row-key="id">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><StatusTag :status="row.status" /></template>
        </el-table-column>
        <el-table-column label="字段数" width="90">
          <template #default="{ row }">{{ row.schema?.materials?.length || 0 }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="edit(row)">编辑</el-button>
            <el-button size="small" link type="primary" @click="preview(row)">预览</el-button>
            <el-button v-if="row.status==='draft'" size="small" link type="success" @click="publish(row)">发布</el-button>
            <el-button v-if="row.status==='published'" size="small" link type="warning" @click="archive(row)">归档</el-button>
            <el-button size="small" link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><EmptyState icon="Document" description="暂无模板，请新建" /></template>
      </el-table>
    </el-card>
  </div>
</template>