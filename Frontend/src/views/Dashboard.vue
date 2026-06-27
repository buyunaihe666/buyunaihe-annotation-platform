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
  { label: '任务总数', value: overview.value.task_count, icon: DataBoard, color: '#4a6cf7' },
  { label: '数据集', value: overview.value.dataset_count, icon: Files, color: '#12b6a6' },
  { label: '标注模板', value: overview.value.template_count, icon: Document, color: '#f5a623' },
  { label: '用户', value: overview.value.user_count, icon: User, color: '#ef5da8' },
  { label: '待审核', value: overview.value.pending_review, icon: Connection, color: '#ec4747' },
  { label: '已完成标注', value: overview.value.completed_items, icon: Notebook, color: '#52c41a' }
])

const pieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0 },
  series: [{
    type: 'pie', radius: ['40%', '68%'], avoidLabelOverlap: true,
    label: { show: true, formatter: '{b}: {c}' },
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
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: tl.map(p => p.date) },
    yAxis: { type: 'value' },
    series: [{ name: '完成数量', type: 'line', smooth: true, areaStyle: { opacity: 0.2 }, data: tl.map(p => p.completed), itemStyle:{ color:'#4a6cf7' } }]
  }
})

const progressOption = computed(() => {
  const s = taskStats.value?.progress
  if (!s) return {}
  const labels = ['待领取','标注中','已提交','AI审核中','已审核','已通过','已驳回','已完成']
  const vals = [s.pending, s.annotating, s.submitted, s.ai_reviewing, s.reviewed, s.approved, s.rejected, s.completed]
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 50, right: 20, top: 30, bottom: 20 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: labels },
    series: [{ type: 'bar', data: vals, itemStyle: { color: '#4a6cf7' }, label: { show: true, position: 'right' } }]
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

    <div class="card-row">
      <div v-for="c in cards" :key="c.label" class="stat-card">
        <div class="icon" :style="{ background: c.color }">
          <el-icon :size="22"><component :is="c.icon" /></el-icon>
        </div>
        <div class="meta">
          <div class="label">{{ c.label }}</div>
          <div class="value">{{ c.value }}</div>
        </div>
      </div>
    </div>

    <el-row :gutter="16" style="margin-top:16px" v-if="isAdmin">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>任务状态分布</template>
          <VChart :option="pieOption" autoresize style="height:300px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>任务进度</span>
              <el-select v-model="selectedTaskId" size="small" style="width:240px" placeholder="选择任务" @change="loadTaskStats">
                <el-option v-for="t in tasks" :key="t.id" :label="t.name" :value="t.id" />
              </el-select>
            </div>
          </template>
          <div v-loading="loadingStats">
            <VChart v-if="taskStats" :option="progressOption" autoresize style="height:300px" />
            <el-empty v-else description="选择任务查看进度" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="margin-top:16px" v-if="isAdmin">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>完成趋势</span>
          <span style="font-size:12px;color:#8a93a6">基于上述任务</span>
        </div>
      </template>
      <VChart v-if="taskStats" :option="timelineOption" autoresize style="height:280px" />
      <el-empty v-else description="选择任务查看趋势" />
    </el-card>
  </div>
</template>