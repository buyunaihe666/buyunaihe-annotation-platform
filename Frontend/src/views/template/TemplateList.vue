<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listTemplates, deleteTemplate, publishTemplate, archiveTemplate, batchDeleteTemplates } from '@/api'
import { useAuthStore } from '@/stores/auth'
import type { Template } from '@/types'
import { TASK_STATUS } from '@/constants'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import EmptyState from '@/components/EmptyState.vue'
import { formatDate } from '@/utils'
import { Delete, Plus } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()
const list = ref<Template[]>([])
const loading = ref(false)
const keyword = ref('')
const selectedIds = ref<number[]>([])
const deleteMode = ref(false)

const filteredList = computed(() => {
  if (!keyword.value.trim()) return list.value
  const kw = keyword.value.trim().toLowerCase()
  return list.value.filter(t =>
    t.name.toLowerCase().includes(kw) ||
    (t.description || '').toLowerCase().includes(kw) ||
    String(t.id).includes(kw)
  )
})

const isAdmin = computed(() => authStore.role === 'admin' || authStore.role === 'owner')
const allSelected = computed(() =>
  filteredList.value.length > 0 && selectedIds.value.length === filteredList.value.length
)
const someSelected = computed(() =>
  selectedIds.value.length > 0 && selectedIds.value.length < filteredList.value.length
)

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

function onSelectionChange(rows: Template[]) {
  selectedIds.value = rows.map(r => r.id)
}

function toggleSelectAll(checked: boolean) {
  if (checked) {
    selectedIds.value = filteredList.value.map(r => r.id)
  } else {
    selectedIds.value = []
  }
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要删除的模板')
    return
  }
  await ElMessageBox.confirm(
    `确定删除选中的 ${selectedIds.value.length} 个模板吗？`,
    '批量删除',
    { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
  )
  await batchDeleteTemplates(selectedIds.value)
  ElMessage.success(`已删除 ${selectedIds.value.length} 个模板`)
  selectedIds.value = []
  deleteMode.value = false
  load()
}

function toggleDeleteMode() {
  deleteMode.value = !deleteMode.value
  if (!deleteMode.value) {
    selectedIds.value = []
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <PageHeader title="标注模板" subtitle="配置数据标注的字段与样表模板" />
    <el-card shadow="never">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input v-model="keyword" placeholder="搜索模板名称" clearable style="width:260px" @clear="load" @keyup.enter="load">
            <template #append><el-button @click="load">搜索</el-button></template>
          </el-input>
        </div>
        <div class="toolbar-right">
          <template v-if="isAdmin && deleteMode">
            <el-checkbox
              :model-value="allSelected"
              :indeterminate="someSelected"
              @change="toggleSelectAll"
            >
              {{ allSelected ? '取消全选' : '全选' }}
            </el-checkbox>
            <el-button
              v-if="selectedIds.length > 0"
              type="danger"
              :icon="Delete"
              @click="handleBatchDelete"
              style="margin-left: 12px"
            >
              删除选中 ({{ selectedIds.length }})
            </el-button>
            <el-button @click="toggleDeleteMode" style="margin-left: 8px">取消</el-button>
          </template>
          <template v-else>
            <el-button
              v-if="isAdmin && list.length > 0"
              :icon="Delete"
              @click="toggleDeleteMode"
            >
              删除
            </el-button>
            <el-button type="primary" :icon="Plus" @click="create" style="margin-left: 8px">新建模板</el-button>
          </template>
        </div>
      </div>
      <el-table :data="filteredList" v-loading="loading" row-key="id" @selection-change="onSelectionChange">
        <el-table-column v-if="isAdmin && deleteMode" type="selection" width="50" />
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
            <el-button v-if="isAdmin" size="small" link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><EmptyState icon="Document" description="暂无模板，请新建" /></template>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.toolbar-left {
  display: flex;
  align-items: center;
}
.toolbar-right {
  display: flex;
  align-items: center;
}

:deep(.el-table__body tr.is-selected > td) {
  background-color: #f5f3ff !important;
}

:deep(.el-table__body tr:hover > td) {
  background-color: #f8fafc !important;
}
</style>
