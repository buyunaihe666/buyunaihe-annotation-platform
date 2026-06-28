<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listDatasets, createDataset, deleteDataset, batchDeleteDatasets } from '@/api'
import { useAuthStore } from '@/stores/auth'
import type { Dataset } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { formatDate } from '@/utils'
import { Search, Delete, Plus } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()
const list = ref<Dataset[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const form = reactive({ name: '', description: '' })
const searchKeyword = ref('')
const selectedIds = ref<number[]>([])
const deleteMode = ref(false)

const isAdmin = computed(() => authStore.role === 'admin' || authStore.role === 'owner')

const filteredList = computed(() => {
  if (!searchKeyword.value.trim()) return list.value
  const kw = searchKeyword.value.trim().toLowerCase()
  return list.value.filter(d =>
    d.name.toLowerCase().includes(kw) ||
    (d.description || '').toLowerCase().includes(kw) ||
    String(d.id).includes(kw)
  )
})

const allSelected = computed(() =>
  filteredList.value.length > 0 && selectedIds.value.length === filteredList.value.length
)

const someSelected = computed(() =>
  selectedIds.value.length > 0 && selectedIds.value.length < filteredList.value.length
)

async function load() {
  loading.value = true
  try {
    list.value = await listDatasets()
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!form.name) { ElMessage.warning('请填写名称'); return }
  await createDataset({ name: form.name, description: form.description })
  ElMessage.success('已创建')
  dialogVisible.value = false
  form.name = ''; form.description = ''
  load()
}

async function remove(row: Dataset) {
  await ElMessageBox.confirm(`删除数据集「${row.name}」？关联数据亦将删除。`, '删除', { type: 'error' })
  await deleteDataset(row.id)
  ElMessage.success('已删除')
  load()
}

function detail(row: Dataset) { router.push(`/datasets/${row.id}`) }

function onSelectionChange(rows: Dataset[]) {
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
    ElMessage.warning('请先选择要删除的数据集')
    return
  }
  await ElMessageBox.confirm(
    `确定删除选中的 ${selectedIds.value.length} 个数据集？关联数据亦将删除。`,
    '批量删除',
    { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
  )
  await batchDeleteDatasets(selectedIds.value)
  ElMessage.success(`已删除 ${selectedIds.value.length} 个数据集`)
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
    <PageHeader title="数据集" subtitle="上传原始数据并管理字段映射" />
    <el-card shadow="never">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索数据集名称、描述..."
            clearable
            :prefix-icon="Search"
            style="width: 300px"
          />
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
              v-if="isAdmin && filteredList.length > 0"
              :icon="Delete"
              @click="toggleDeleteMode"
            >
              删除
            </el-button>
            <el-button type="primary" :icon="Plus" @click="dialogVisible = true" style="margin-left: 8px">新建数据集</el-button>
          </template>
        </div>
      </div>

      <el-table
        :data="filteredList"
        v-loading="loading"
        @selection-change="onSelectionChange"
        row-key="id"
      >
        <el-table-column v-if="isAdmin && deleteMode" type="selection" width="50" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="format" label="格式" width="100" />
        <el-table-column prop="file_count" label="文件数" width="90" />
        <el-table-column prop="item_count" label="样本数" width="90" />
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="detail(row)">详情</el-button>
            <el-button v-if="isAdmin" size="small" link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><EmptyState icon="Files" description="暂无数据集" /></template>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新建数据集" width="480px">
      <el-form :model="form" label-position="top">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">创建</el-button>
      </template>
    </el-dialog>
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
