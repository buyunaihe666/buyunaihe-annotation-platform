<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getTask, getTaskProgress, getAssignees, assignTask,
  getTaskItems, publishTask, pauseTask, completeTask, listUsers, createExport, listExports, getTaskStats
} from '@/api'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import type { Task, TaskProgress, TaskAssignment, User, TaskItem, ExportRecord } from '@/types'
import { TASK_ITEM_STATUS, EXPORT_FORMATS, ROLE_LABEL, REVIEW_DECISIONS } from '@/constants'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import EmptyState from '@/components/EmptyState.vue'
import { usePagination } from '@/composables/usePagination'
import { formatDate, formatSize } from '@/utils'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent])

const route = useRoute()
const router = useRouter()
const id = computed(() => Number(route.params.id))

const task = ref<Task | null>(null)
const progress = ref<TaskProgress>({ total:0, pending:0, annotating:0, submitted:0, ai_reviewing:0, reviewed:0, approved:0, rejected:0, completed:0 })
const labelerStats = ref<any[]>([])

const assignees = ref<TaskAssignment[]>([])
const users = ref<User[]>([])
const labelers = computed(() => users.value.filter(u => ['labeler', 'admin', 'owner'].includes(u.role_code)))
const reviewers = computed(() => users.value.filter(u => ['reviewer', 'admin', 'owner'].includes(u.role_code)))

const items = ref<TaskItem[]>([])
const loadingItems = ref(false)
const { page, size, total, setPage, setSize, setTotal } = usePagination(20)
const itemStatusFilter = ref('')

const exportDialogVisible = ref(false)
const exportForm = reactive({ format: 'json' })
const exportRecords = ref<ExportRecord[]>([])
const exporting = ref(false)

const progressOption = computed(() => {
  const labels = ['待领取','标注中','已提交','AI审核中','已审核','已通过','已驳回','已完成']
  const vals = [progress.value.pending, progress.value.annotating, progress.value.submitted, progress.value.ai_reviewing, progress.value.reviewed, progress.value.approved, progress.value.rejected, progress.value.completed]
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 60, right: 20, top: 20, bottom: 20 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: labels },
    series: [{ type: 'bar', data: vals, itemStyle: { color: '#4a6cf7' }, label: { show: true, position: 'right' } }]
  }
})

async function loadTask() {
  task.value = await getTask(id.value)
  progress.value = await getTaskProgress(id.value)
  assignees.value = await getAssignees(id.value)
  try {
    const stats = await getTaskStats(id.value)
    labelerStats.value = stats.labeler_stats || []
  } catch { labelerStats.value = [] }
}

async function loadItems() {
  loadingItems.value = true
  try {
    const res = await getTaskItems(id.value, { status: itemStatusFilter.value || undefined, page: page.value, size: size.value })
    items.value = res.items || []
    setTotal(res.total || 0)
  } finally {
    loadingItems.value = false
  }
}

async function loadExports() {
  exportRecords.value = await listExports(id.value)
}

async function loadUsers() {
  users.value = await listUsers()
}

function onPage(p: number) { setPage(p); loadItems() }
function onSize(s: number) { setSize(s); loadItems() }

const assignDialogVisible = ref(false)
const assignForm = reactive({ labeler_id: undefined as number | undefined, reviewer_id: undefined as number | undefined })

async function saveAssign() {
  const assignments: { user_id: number; role: string }[] = []
  if (assignForm.labeler_id) assignments.push({ user_id: assignForm.labeler_id, role: 'labeler' })
  if (assignForm.reviewer_id) assignments.push({ user_id: assignForm.reviewer_id, role: 'reviewer' })
  if (!assignments.length) { ElMessage.warning('请选择要分配的用户'); return }
  await assignTask(id.value, assignments)
  ElMessage.success('已分配')
  assignDialogVisible.value = false
  assignees.value = await getAssignees(id.value)
}

function userLabel(uid?: number) {
  const u = users.value.find(x => x.id === uid)
  return u ? `${u.nickname || u.username} (id:${u.id})` : `${uid}`
}

async function publishTaskAction() {
  await ElMessageBox.confirm('发布任务？将生成全部标注项。', '发布', { type: 'warning' })
  await publishTask(id.value)
  ElMessage.success('已发布')
  loadTask()
}

async function pauseAction() {
  await pauseTask(id.value)
  ElMessage.success('已暂停')
  loadTask()
}
async function completeAction() {
  await completeTask(id.value)
  ElMessage.success('任务已完成')
  loadTask()
}

async function createExportRecord() {
  exporting.value = true
  try {
    await createExport(id.value, exportForm.format)
    ElMessage.success('导出任务已创建')
    exportDialogVisible.value = false
    await loadExports()
  } finally {
    exporting.value = false
  }
}

function exportDownloadUrl(recId: number) {
  return `/api/export/${recId}/download`
}

onMounted(async () => {
  await loadTask()
  await loadItems()
  await loadUsers()
  await loadExports()
})
</script>

<template>
  <div class="page">
    <PageHeader :title="`任务 · ${task?.name || ''}`" :subtitle="task?.description" />
    <el-button @click="router.back()">返回</el-button>

    <el-row :gutter="16" style="margin-top:12px">
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>任务状态</template>
          <div v-if="task">
            <el-space wrap>
              <StatusTag :status="task.status" />
              <el-tag size="small" effect="plain">模板：{{ task.template?.name || task.template_id }}</el-tag>
              <el-tag size="small" effect="plain">数据集：{{ task.dataset?.name || task.dataset_id }}</el-tag>
              <el-tag v-if="task.enable_ai_audit" size="small" type="success" effect="plain">AI 审核</el-tag>
              <el-tag v-if="task.enable_ai_suggestion" size="small" type="success" effect="plain">AI 建议</el-tag>
            </el-space>
            <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap">
              <el-button v-if="task.status==='draft'" size="small" type="success" @click="publishTaskAction">发布</el-button>
              <el-button v-if="task.status==='published'" size="small" type="warning" @click="pauseAction">暂停</el-button>
              <el-button v-if="task.status==='paused'" size="small" type="success" @click="publishTaskAction">恢复</el-button>
              <el-button v-if="['published','paused'].includes(task.status)" size="small" @click="completeAction">完成</el-button>
              <el-button size="small" @click="router.push(`/tasks/${id}/edit`)">编辑</el-button>
              <el-button size="small" type="primary" @click="exportDialogVisible = true">导出</el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>进度统计</span>
              <span style="font-size:12px;color:#8a93a6">总计 {{ progress.total }} 条</span>
            </div>
          </template>
          <el-progress :percentage="progress.total ? Math.round((progress.completed / progress.total) * 100) : 0" :stroke-width="10" />
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:12px">
            <div class="mini-stat"><div class="v">{{ progress.pending }}</div><div class="l">待领取</div></div>
            <div class="mini-stat"><div class="v">{{ progress.annotating }}</div><div class="l">标注中</div></div>
            <div class="mini-stat"><div class="v">{{ progress.submitted }}</div><div class="l">已提交</div></div>
            <div class="mini-stat"><div class="v">{{ progress.ai_reviewing }}</div><div class="l">AI审核中</div></div>
            <div class="mini-stat"><div class="v">{{ progress.reviewed }}</div><div class="l">已审核</div></div>
            <div class="mini-stat"><div class="v">{{ progress.approved }}</div><div class="l">已通过</div></div>
            <div class="mini-stat"><div class="v">{{ progress.rejected }}</div><div class="l">已驳回</div></div>
            <div class="mini-stat"><div class="v">{{ progress.completed }}</div><div class="l">已完成</div></div>
          </div>
          <VChart v-if="progress.total" :option="progressOption" autoresize style="height:260px;margin-top:12px" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="margin-top:16px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>分配人员</span>
          <el-button size="small" type="primary" @click="assignDialogVisible = true">分配</el-button>
        </div>
      </template>
      <el-empty v-if="!assignees.length" description="尚未分配" :image-size="60" />
      <el-table v-else :data="assignees" border size="small">
        <el-table-column label="用户" min-width="200"><template #default="{ row }">{{ userLabel(row.user_id) }}</template></el-table-column>
        <el-table-column label="角色" width="120"><template #default="{ row }">{{ ROLE_LABEL[row.role as keyof typeof ROLE_LABEL] || row.role }}</template></el-table-column>
        <el-table-column label="分配时间" width="180"><template #default="{ row }">{{ formatDate(row.assigned_at) }}</template></el-table-column>
      </el-table>
      <div v-if="labelerStats.length" style="margin-top:12px">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px">标注员绩效</div>
        <el-table :data="labelerStats" border size="small">
          <el-table-column label="标注员"><template #default="{ row }">{{ row.nickname || row.username }}</template></el-table-column>
          <el-table-column prop="annotated" label="已标注" width="100" />
          <el-table-column prop="approved" label="通过" width="100" />
          <el-table-column prop="rejected" label="驳回" width="100" />
        </el-table>
      </div>
    </el-card>

    <el-card shadow="never" style="margin-top:16px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>标注项</span>
          <el-select v-model="itemStatusFilter" placeholder="状态筛选" clearable size="small" style="width:160px" @change="() => { setPage(1); loadItems() }">
            <el-option v-for="(v, k) in TASK_ITEM_STATUS" :key="k" :label="v.label" :value="k" />
          </el-select>
        </div>
      </template>
      <el-table :data="items" v-loading="loadingItems" border stripe size="small">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="index" label="序号" width="80" />
        <el-table-column label="状态" width="110"><template #default="{ row }"><StatusTag :status="row.status" /></template></el-table-column>
        <el-table-column label="标注员" width="140"><template #default="{ row }">{{ userLabel(row.assigned_labeler_id) }}</template></el-table-column>
        <el-table-column label="审核员" width="140"><template #default="{ row }">{{ userLabel(row.assigned_reviewer_id) }}</template></el-table-column>
        <el-table-column label="更新时间" width="170"><template #default="{ row }">{{ formatDate(row.updated_at) }}</template></el-table-column>
        <template #empty><EmptyState icon="List" description="暂无标注项" /></template>
      </el-table>
      <el-pagination
        style="margin-top:12px;justify-content:flex-end;display:flex"
        :current-page="page" :page-size="size" :total="total"
        layout="total, prev, pager, next, sizes"
        @current-change="onPage" @size-change="onSize"
      />
    </el-card>

    <el-card shadow="never" style="margin-top:16px">
      <template #header>导出记录</template>
      <el-empty v-if="!exportRecords.length" description="暂无导出记录" :image-size="60" />
      <el-table v-else :data="exportRecords" border size="small">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="format" label="格式" width="100" />
        <el-table-column prop="total" label="条数" width="100" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column label="创建时间" width="170"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
        <el-table-column label="文件" min-width="220">
          <template #default="{ row }">
            <div v-if="row.files?.length">
              <a v-for="f in row.files" :key="f.id" :href="f.url" target="_blank" style="margin-right:10px;color:#4a6cf7">
                {{ f.filename }} ({{ formatSize(f.size) }})
              </a>
            </div>
            <span v-else style="color:#a0a6b5">生成中...</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="assignDialogVisible" title="分配人员" width="460px">
      <el-form label-position="top">
        <el-form-item label="分配标注员">
          <el-select v-model="assignForm.labeler_id" clearable placeholder="选择标注员" style="width:100%">
            <el-option v-for="u in labelers" :key="u.id" :label="`${u.nickname || u.username} (id:${u.id})`" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="分配审核员">
          <el-select v-model="assignForm.reviewer_id" clearable placeholder="选择审核员" style="width:100%">
            <el-option v-for="u in reviewers" :key="u.id" :label="`${u.nickname || u.username} (id:${u.id})`" :value="u.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveAssign">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="exportDialogVisible" title="创建导出" width="420px">
      <el-form label-position="top">
        <el-form-item label="导出格式">
          <el-radio-group v-model="exportForm.format">
            <el-radio v-for="f in EXPORT_FORMATS" :key="f.value" :value="f.value">{{ f.label }}</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exportDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="exporting" @click="createExportRecord">创建导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.mini-stat { background:#f6f8fa; border-radius:8px; padding:8px 10px; text-align:center; }
.mini-stat .v { font-size:18px; font-weight:700; color:#1f2430; }
.mini-stat .l { font-size:12px; color:#8a93a6; }
</style>