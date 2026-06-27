<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSquare, claimItem } from '@/api'
import type { Task } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import EmptyState from '@/components/EmptyState.vue'
import { formatDate } from '@/utils'

const router = useRouter()
const list = ref<Task[]>([])
const loading = ref(false)
const keyword = ref('')
const claiming = ref<number | null>(null)

async function load() {
  loading.value = true
  try {
    list.value = await getSquare({ keyword: keyword.value || undefined })
  } finally {
    loading.value = false
  }
}

async function claim(task: Task) {
  claiming.value = task.id
  try {
    const res = await claimItem(task.id)
    ElMessage.success('已领取任务，开始标注')
    router.push(`/workbench/${res.task_item_id}`)
  } catch {
    // ignored
  } finally {
    claiming.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <PageHeader title="标注广场" subtitle="领取已发布任务进入标注工作台" />
    <el-card shadow="never">
      <div style="margin-bottom:12px">
        <el-input v-model="keyword" placeholder="搜索任务名称" clearable style="width:280px" @keyup.enter="load">
          <template #append><el-button @click="load">搜索</el-button></template>
        </el-input>
      </div>
      <el-empty v-if="!list.length && !loading" description="暂无可领取任务">
        <el-button @click="load">刷新</el-button>
      </el-empty>
      <el-row :gutter="16">
        <el-col v-for="t in list" :key="t.id" :span="8" style="margin-bottom:16px">
          <el-card shadow="hover" class="task-card">
            <div class="tc-head">
              <span class="tc-name">{{ t.name }}</span>
              <StatusTag :status="t.status" />
            </div>
            <div class="tc-desc">{{ t.description || '无描述' }}</div>
            <div class="tc-meta">
              <span>{{ t.template?.name || '关联模板' }}</span>
              <span>·</span>
              <span>{{ t.dataset?.name || '数据集' }}</span>
              <span v-if="t.enable_ai_suggestion">· AI 建议</span>
              <span v-if="t.enable_ai_audit">· AI 审核</span>
            </div>
            <div class="tc-meta sm">{{ formatDate(t.created_at) }}</div>
            <el-button type="primary" :loading="claiming === t.id" @click="claim(t)">领取并开始</el-button>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<style scoped>
.task-card { border-radius:10px; }
.tc-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.tc-name { font-weight:600; color:#1f2430; }
.tc-desc { color:#8a93a6; font-size:13px; min-height:38px; }
.tc-meta { color:#a0a6b5; font-size:12px; margin-top:8px; display:flex; gap:6px; flex-wrap:wrap; }
.tc-meta.sm { margin-top:2px; }
.el-button { margin-top:12px; width:100%; }
</style>