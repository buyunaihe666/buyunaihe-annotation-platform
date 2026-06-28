<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listExports, listTasks, downloadExportFile, previewExportContent, deleteExport, batchDeleteExports } from '@/api'
import { useAuthStore } from '@/stores/auth'
import type { ExportRecord, Task } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { formatDate, formatSize } from '@/utils'
import { Download, Refresh, Search, View, Document, Delete } from '@element-plus/icons-vue'

const records = ref<ExportRecord[]>([])
const tasks = ref<Task[]>([])
const loading = ref(false)
const taskFilter = ref<number | undefined>(undefined)
const searchKeyword = ref('')
const selectedIds = ref<number[]>([])
const deleteMode = ref(false)

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.role === 'admin' || authStore.role === 'owner')

// Preview dialog
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewContent = ref('')
const previewFormat = ref('')
const previewFilename = ref('')
const previewTotal = ref(0)

const isJsonFormat = computed(() => previewFormat.value === 'json')

const filteredRecords = computed(() => {
  let list = records.value
  if (searchKeyword.value.trim()) {
    const kw = searchKeyword.value.trim().toLowerCase()
    const taskMap = new Map(tasks.value.map(t => [t.id, t.name]))
    list = list.filter(r => {
      const tname = (taskMap.get(r.task_id) || `任务 #${r.task_id}`).toLowerCase()
      const fmt = (r.format || '').toLowerCase()
      return tname.includes(kw) || fmt.includes(kw) || String(r.id).includes(kw)
    })
  }
  return list
})

const csvHeaders = computed<string[]>(() => {
  if (isJsonFormat.value || !previewContent.value) return []
  const lines = previewContent.value.split('\n').filter(Boolean)
  if (lines.length === 0) return []
  return lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''))
})
const csvRows = computed<string[][]>(() => {
  if (isJsonFormat.value || !previewContent.value) return []
  const lines = previewContent.value.split('\n').filter(Boolean)
  if (lines.length <= 1) return []
  return lines.slice(1).map(line => {
    const vals: string[] = []
    let current = ''
    let inQuotes = false
    for (const ch of line) {
      if (ch === '"') { inQuotes = !inQuotes; continue }
      if (ch === ',' && !inQuotes) { vals.push(current.trim()); current = ''; continue }
      current += ch
    }
    vals.push(current.trim())
    return vals
  }).slice(0, 100)
})

async function load() {
  loading.value = true
  try {
    records.value = await listExports(taskFilter.value)
  } finally {
    loading.value = false
  }
}

function taskName(tid?: number) {
  const t = tasks.value.find(x => x.id === tid)
  return t ? t.name : `任务 #${tid}`
}

function formatStatus(status: string) {
  const map: Record<string, string> = {
    pending: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return map[status] || status
}

function toggleSelectAll(checked: boolean) {
  if (checked) {
    selectedIds.value = filteredRecords.value.map(r => r.id)
  } else {
    selectedIds.value = []
  }
}

function toggleSelect(id: number) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要删除的导出记录')
    return
  }
  await ElMessageBox.confirm(
    `确定删除选中的 ${selectedIds.value.length} 条导出记录？`,
    '批量删除',
    { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
  )
  await batchDeleteExports(selectedIds.value)
  ElMessage.success(`已删除 ${selectedIds.value.length} 条记录`)
  selectedIds.value = []
  deleteMode.value = false
  await load()
}

function toggleDeleteMode() {
  deleteMode.value = !deleteMode.value
  if (!deleteMode.value) {
    selectedIds.value = []
  }
}

async function handleSingleDelete(rec: ExportRecord) {
  await ElMessageBox.confirm(
    `确定删除「${taskName(rec.task_id)}」的导出记录？`,
    '删除',
    { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
  )
  await deleteExport(rec.id)
  ElMessage.success('已删除')
  await load()
}

async function handleDownload(rec: ExportRecord) {
  if (rec.status !== 'completed' || !rec.files?.length) {
    ElMessage.warning('暂无可用文件')
    return
  }
  try {
    const blob = await downloadExportFile(rec.id)
    const filename = rec.files[0]?.filename || `export_${rec.id}`
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('下载失败，请重试')
  }
}

async function handlePreview(rec: ExportRecord) {
  if (rec.status !== 'completed' || !rec.files?.length) {
    ElMessage.warning('暂无可用文件')
    return
  }
  const fmt = (rec.format || '').toLowerCase()
  if (fmt !== 'json' && fmt !== 'csv') {
    ElMessage.info('仅支持 JSON 和 CSV 格式的在线预览')
    return
  }
  previewLoading.value = true
  previewVisible.value = true
  previewFormat.value = fmt
  previewFilename.value = rec.files[0]?.filename || ''
  previewTotal.value = rec.total || 0
  try {
    const text = await previewExportContent(rec.id)
    previewContent.value = text
  } catch {
    ElMessage.error('预览加载失败')
    previewContent.value = ''
  } finally {
    previewLoading.value = false
  }
}

function getTruncatedPreview(text: string): string {
  const lines = text.split('\n')
  if (lines.length > 500) {
    return lines.slice(0, 500).join('\n') + '\n\n... (已截断，仅显示前500行)'
  }
  return text
}

const truncatedJson = computed(() => {
  if (!isJsonFormat.value || !previewContent.value) return ''
  try {
    const parsed = JSON.parse(previewContent.value)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return getTruncatedPreview(previewContent.value)
  }
})

onMounted(async () => {
  tasks.value = await listTasks()
  await load()
})
</script>

<template>
  <div class="page">
    <PageHeader title="导出记录" subtitle="查看和管理所有任务的导出文件" />

    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索任务名称、格式..."
          clearable
          :prefix-icon="Search"
          style="width: 280px"
          class="search-input"
        />
        <el-select
          v-model="taskFilter"
          placeholder="按任务筛选"
          clearable
          style="width: 220px; margin-left: 12px"
          @change="load"
        >
          <el-option v-for="t in tasks" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <template v-if="isAdmin && deleteMode">
          <el-button
            @click="toggleSelectAll(selectedIds.length !== filteredRecords.length)"
            style="margin-left: 8px"
          >
            {{ selectedIds.length === filteredRecords.length ? '取消全选' : '全选' }}
          </el-button>
          <el-button
            v-if="selectedIds.length > 0"
            type="danger"
            :icon="Delete"
            @click="handleBatchDelete"
            style="margin-left: 8px"
          >
            删除选中 ({{ selectedIds.length }})
          </el-button>
          <el-button @click="toggleDeleteMode" style="margin-left: 8px">取消</el-button>
        </template>
        <template v-else>
          <el-button
            v-if="isAdmin && filteredRecords.length > 0"
            :icon="Delete"
            @click="toggleDeleteMode"
            style="margin-left: 8px"
          >
            删除
          </el-button>
          <el-button :icon="Refresh" @click="load" style="margin-left: 8px">刷新</el-button>
        </template>
      </div>
    </div>

    <div class="export-list">
      <div v-if="loading" v-loading="loading" class="loading-mask" />

      <template v-if="!loading && filteredRecords.length === 0">
        <EmptyState icon="Download" title="暂无导出记录" description="请先在任务中创建导出" />
      </template>

      <div v-for="rec in filteredRecords" :key="rec.id" class="export-card" :class="{ 'is-selected': selectedIds.includes(rec.id) }">
        <div class="checkbox-col" v-if="isAdmin && deleteMode">
          <el-checkbox
            :model-value="selectedIds.includes(rec.id)"
            @change="() => toggleSelect(rec.id)"
          />
        </div>
        <div class="card-left">
          <div class="card-icon" :class="rec.status">
            <el-icon :size="20"><Download /></el-icon>
          </div>
        </div>
        <div class="card-body">
          <div class="card-top">
            <div class="card-title">{{ taskName(rec.task_id) }}</div>
            <el-tag
              size="small"
              :type="rec.status === 'completed' ? 'success' : rec.status === 'failed' ? 'danger' : 'warning'"
              effect="plain"
              class="status-tag"
            >
              {{ formatStatus(rec.status) }}
            </el-tag>
          </div>
          <div class="card-meta">
            <span class="meta-item">
              <span class="meta-label">格式</span>
              <span class="meta-value">{{ rec.format?.toUpperCase() }}</span>
            </span>
            <span class="meta-divider" />
            <span class="meta-item">
              <span class="meta-label">条数</span>
              <span class="meta-value">{{ rec.total || 0 }}</span>
            </span>
            <span class="meta-divider" />
            <span class="meta-item">
              <span class="meta-label">创建时间</span>
              <span class="meta-value">{{ formatDate(rec.created_at) }}</span>
            </span>
          </div>
          <div v-if="rec.files?.length" class="card-files">
            <div v-for="f in rec.files" :key="f.id" class="file-chip">
              <el-icon><Document /></el-icon>
              <span class="file-name">{{ f.filename }}</span>
              <span class="file-size">({{ formatSize(f.size) }})</span>
            </div>
          </div>
        </div>
        <div class="card-actions">
          <template v-if="rec.status === 'completed' && rec.files?.length">
            <el-button plain size="small" :icon="View" @click="handlePreview(rec)"
              :disabled="rec.format !== 'json' && rec.format !== 'csv'">预览</el-button>
            <el-button type="primary" size="small" :icon="Download" @click="handleDownload(rec)">下载</el-button>
          </template>
          <span v-else class="pending-text">
            {{ rec.status === 'pending' ? '生成中...' : '无文件' }}
          </span>
          <el-button v-if="isAdmin" size="small" link type="danger" :icon="Delete" @click="handleSingleDelete(rec)" style="margin-left:8px">删除</el-button>
        </div>
      </div>
    </div>

    <!-- Preview Dialog -->
    <el-dialog v-model="previewVisible" :title="`在线预览 - ${previewFilename}`" width="80%"
      :close-on-click-modal="false" top="5vh" destroy-on-close>
      <div v-loading="previewLoading" class="preview-body">
        <template v-if="!isJsonFormat && csvHeaders.length > 0">
          <div class="preview-info">
            <span>共 {{ previewTotal }} 条记录 | 显示前 {{ Math.min(csvRows.length, 100) }} 行</span>
          </div>
          <div class="csv-table-wrap">
            <table class="csv-table">
              <thead><tr><th v-for="h in csvHeaders" :key="h" :title="h">{{ h }}</th></tr></thead>
              <tbody>
                <tr v-for="(row, ri) in csvRows" :key="ri">
                  <td v-for="(cell, ci) in row" :key="ci" :title="cell">{{ cell }}</td>
                </tr>
                <tr v-if="csvRows.length === 0"><td :colspan="csvHeaders.length" class="empty-row">暂无数据</td></tr>
              </tbody>
            </table>
          </div>
        </template>
        <template v-else-if="isJsonFormat">
          <div class="preview-info"><span>共 {{ previewTotal }} 条记录</span></div>
          <pre class="json-preview"><code>{{ truncatedJson }}</code></pre>
        </template>
        <template v-else-if="!previewLoading && !previewContent">
          <el-empty description="暂无预览内容" :image-size="80" />
        </template>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <span class="footer-info">仅显示前 500 行 / 100 条 | 完整内容请下载查看</span>
          <el-button @click="previewVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.toolbar-left {
  display: flex;
  align-items: center;
}

.export-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.export-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: #fff;
  border: 1px solid var(--lh-border);
  border-radius: 12px;
  transition: all 0.2s ease;

  &:hover {
    border-color: #cbd5e1;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
  }
}

.checkbox-col {
  flex-shrink: 0;
  padding-right: 4px;
}

.card-left { flex-shrink: 0; }

.card-icon {
  width: 44px; height: 44px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  background: var(--lh-primary-light); color: var(--lh-primary);
  &.completed { background: #ecfdf5; color: var(--lh-success); }
  &.pending { background: #fffbeb; color: var(--lh-warning); }
  &.failed { background: #fef2f2; color: var(--lh-danger); }
}

.card-body { flex: 1; min-width: 0; }

.card-top { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.card-title { font-weight: 600; font-size: 15px; color: var(--lh-text); }
.status-tag { flex-shrink: 0; }

.card-meta { display: flex; align-items: center; gap: 12px; font-size: 13px; color: var(--lh-text-soft); }
.meta-item { display: flex; align-items: center; gap: 4px; }
.meta-label { color: var(--lh-text-soft); }
.meta-value { color: var(--lh-text); font-weight: 500; }
.meta-divider { width: 1px; height: 12px; background: var(--lh-border); }

.card-files { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.file-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 12px; background: #f8fafc;
  border: 1px solid var(--lh-border); border-radius: 8px;
  font-size: 12px; color: #64748b;
}
.file-name { font-weight: 500; color: var(--lh-text); }
.file-size { color: var(--lh-text-soft); }

.card-actions {
  flex-shrink: 0;
  margin-left: auto;
  padding-left: 16px;
  border-left: 1px solid var(--lh-border);
  display: flex;
  align-items: center;
  gap: 6px;
}

.pending-text { font-size: 13px; color: var(--lh-text-soft); white-space: nowrap; }
.loading-mask { min-height: 200px; }

/* Selected card highlight */
.export-card.is-selected {
  background: #f5f3ff;
  border-color: #c4b5fd;
}

/* Preview */
.preview-body { min-height: 300px; max-height: 65vh; overflow: auto; }
.preview-info { padding: 8px 0 12px; font-size: 13px; color: #6b7280; border-bottom: 1px solid #f3f4f6; margin-bottom: 12px; }
.csv-table-wrap { overflow: auto; max-height: 55vh; }
.csv-table {
  width: 100%; border-collapse: collapse; font-size: 13px;
  th, td { padding: 8px 12px; text-align: left; border: 1px solid #e5e7eb; white-space: nowrap; max-width: 300px; overflow: hidden; text-overflow: ellipsis; }
  th { background: #f8fafc; color: #374151; font-weight: 600; position: sticky; top: 0; z-index: 1; }
  td { color: #4b5563; }
  tr:nth-child(even) td { background: #f9fafb; }
  tr:hover td { background: #f3f4f6; }
  .empty-row { text-align: center; color: #9ca3af; padding: 24px; }
}
.json-preview {
  margin: 0; padding: 16px; background: #1e293b; border-radius: 8px;
  font-size: 13px; line-height: 1.6; overflow: auto; max-height: 55vh; color: #e2e8f0;
}
.dialog-footer { display: flex; justify-content: space-between; align-items: center; }
.footer-info { font-size: 12px; color: #9ca3af; }
</style>
