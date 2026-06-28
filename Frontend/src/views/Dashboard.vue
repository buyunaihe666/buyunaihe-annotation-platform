<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart, LineChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent, GridComponent
} from 'echarts/components'
import { getOverview, getTaskStats, listTasks } from '@/api'
import type { StatsOverview, TaskStatsResponse, Task } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { DataBoard, Files, Document, User, Notebook, Connection } from '@element-plus/icons-vue'

use([CanvasRenderer, PieChart, BarChart, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const auth = useAuthStore()
const overview = ref<StatsOverview>({ task_count:0, dataset_count:0, template_count:0, user_count:0, pending_review:0, completed_items:0 })
const tasks = ref<Task[]>([])
const selectedTaskId = ref<number | undefined>()
const taskStats = ref<TaskStatsResponse | null>(null)
const loadingStats = ref(false)

const isAdmin = computed(() => auth.user?.role_code === 'owner' || auth.user?.role_code === 'admin')

const cards = computed(() => [
  { label: '任务总数', value: overview.value.task_count, icon: DataBoard, color: '#6366f1', gradient: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)' },
  { label: '数据集', value: overview.value.dataset_count, icon: Files, color: '#10b981', gradient: 'linear-gradient(135deg, #10b981 0%, #34d399 100%)' },
  { label: '标注模板', value: overview.value.template_count, icon: Document, color: '#f59e0b', gradient: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)' },
  { label: '用户', value: overview.value.user_count, icon: User, color: '#ec4899', gradient: 'linear-gradient(135deg, #ec4899 0%, #f472b6 100%)' },
  { label: '待审核', value: overview.value.pending_review, icon: Connection, color: '#ef4444', gradient: 'linear-gradient(135deg, #ef4444 0%, #f87171 100%)' },
  { label: '已完成标注', value: overview.value.completed_items, icon: Notebook, color: '#3b82f6', gradient: 'linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%)' }
])

const pieOption = computed(() => ({
  tooltip: { trigger: 'item', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#e5e7eb', borderWidth: 1, textStyle: { color: '#374151' } },
  legend: { bottom: 0, textStyle: { color: '#6b7280' } },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    avoidLabelOverlap: true,
    itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
    label: { show: true, formatter: '{b}: {c}', color: '#4b5563' },
    data: pieData.value
  }]
}))

const pieData = computed(() => {
  const ts = tasks.value
  const groups: Record<string, number> = {}
  for (const t of ts) groups[t.status] = (groups[t.status] || 0) + 1
  const map: Record<string, string> = { draft: '草稿', published: '已发布', paused: '已暂停', completed: '已完成', archived: '已归档' }
  return Object.keys(groups).map(k => ({ name: map[k] || k, value: groups[k] }))
})

const timelineOption = computed(() => {
  const tl = taskStats.value?.timeline || []
  return {
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#e5e7eb', borderWidth: 1, textStyle: { color: '#374151' } },
    grid: { left: 50, right: 30, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: tl.map(p => p.date), axisLine: { lineStyle: { color: '#e5e7eb' } }, axisLabel: { color: '#6b7280' } },
    yAxis: { type: 'value', axisLine: { show: false }, splitLine: { lineStyle: { color: '#f3f4f6' } }, axisLabel: { color: '#6b7280' } },
    series: [{ name: '完成数量', type: 'line', smooth: true, areaStyle: { opacity: 0.15, color: '#6366f1' }, data: tl.map(p => p.completed), itemStyle:{ color:'#6366f1' }, lineStyle: { width: 3 } }]
  }
})

const progressOption = computed(() => {
  const s = taskStats.value?.progress
  if (!s) return {}
  const labels = ['待领取','标注中','已提交','AI审核中','已审核','已通过','已驳回','已完成']
  const vals = [s.pending, s.annotating, s.submitted, s.ai_reviewing, s.reviewed, s.approved, s.rejected, s.completed]
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#e5e7eb', borderWidth: 1, textStyle: { color: '#374151' } },
    grid: { left: 70, right: 30, top: 30, bottom: 20 },
    xAxis: { type: 'value', axisLine: { show: false }, splitLine: { lineStyle: { color: '#f3f4f6' } }, axisLabel: { color: '#6b7280' } },
    yAxis: { type: 'category', data: labels, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: '#4b5563' } },
    series: [{ type: 'bar', data: vals, itemStyle: { color: '#6366f1', borderRadius: [0, 4, 4, 0] }, label: { show: true, position: 'right', color: '#4b5563' }, barWidth: '60%' }]
  }
})

async function loadOverview() {
  overview.value = await getOverview()
  tasks.value = await listTasks()
  if (tasks.value.length) {
    selectedTaskId.value = tasks.value[0].id
    await loadTaskStats()
  }
}

async function loadTaskStats() {
  if (!selectedTaskId.value) return
  loadingStats.value = true
  try {
    taskStats.value = await getTaskStats(selectedTaskId.value)
  } finally {
    loadingStats.value = false
  }
}

onMounted(loadOverview)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>数据看板</h2>
      <div class="sub">{{ auth.user?.nickname }}，欢迎回到 Buyunaihe 平台</div>
    </div>

    <div class="stat-grid">
      <div v-for="c in cards" :key="c.label" class="stat-card">
        <div class="card-left">
          <div class="icon" :style="{ background: c.gradient }">
            <el-icon :size="24"><component :is="c.icon" /></el-icon>
          </div>
        </div>
        <div class="card-right">
          <div class="label">{{ c.label }}</div>
          <div class="value">{{ c.value }}</div>
        </div>
      </div>
    </div>

    <div class="charts-container" v-if="isAdmin">
      <div class="chart-card">
        <div class="chart-header">
          <span class="chart-title">任务状态分布</span>
        </div>
        <VChart :option="pieOption" autoresize class="chart" />
      </div>
      <div class="chart-card">
        <div class="chart-header">
          <span class="chart-title">任务进度</span>
          <el-select v-model="selectedTaskId" placeholder="选择任务" @change="loadTaskStats">
            <el-option v-for="t in tasks" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </div>
        <div v-loading="loadingStats" class="chart-content">
          <VChart v-if="taskStats" :option="progressOption" autoresize class="chart" />
          <el-empty v-else description="选择任务查看进度" :image-size="60" />
        </div>
      </div>
    </div>

    <div class="chart-card full-width" v-if="isAdmin">
      <div class="chart-header">
        <span class="chart-title">完成趋势</span>
        <span class="chart-subtitle">基于上述任务</span>
      </div>
      <VChart v-if="taskStats" :option="timelineOption" autoresize class="chart" />
      <el-empty v-else description="选择任务查看趋势" :image-size="60" />
    </div>
  </div>
</template>

<style scoped lang="scss">
.page {
  min-height: calc(100vh - 64px);
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
}

.page-header {
  padding: 24px 32px 0;
  margin-bottom: 24px;

  h2 {
    font-size: 24px;
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 6px 0;
  }

  .sub {
    font-size: 14px;
    color: #6b7280;
  }
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  padding: 0 32px;
  margin-bottom: 24px;
}

.stat-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  border: 1px solid #f3f4f6;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 24px rgba(99, 102, 241, 0.1);
    border-color: #e0e7ff;
  }

  .card-left {
    flex-shrink: 0;
  }

  .icon {
    width: 56px;
    height: 56px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ffffff;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
  }

  .card-right {
    flex: 1;
  }

  .label {
    font-size: 14px;
    color: #6b7280;
    margin-bottom: 4px;
  }

  .value {
    font-size: 32px;
    font-weight: 700;
    color: #1f2937;
    line-height: 1;
  }
}

.charts-container {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  padding: 0 32px;
  margin-bottom: 20px;
}

.chart-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #f3f4f6;

  &.full-width {
    margin: 0 32px 32px;
  }
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f3f4f6;
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.chart-subtitle {
  font-size: 13px;
  color: #9ca3af;
}

.chart {
  height: 300px;
}

.chart-content {
  min-height: 300px;
}

:deep(.el-select) {
  width: 260px;
}

:deep(.el-empty__description) {
  color: #9ca3af;
}
</style>
