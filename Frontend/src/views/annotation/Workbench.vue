<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAnnotationItem, saveDraft, submitItem, requestSuggestion, getSuggestion } from '@/api'
import type { AnnotationItemResponse, TemplateSchema, TaskItem } from '@/types'
import MaterialRenderer from '@/components/MaterialRenderer.vue'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { TASK_ITEM_STATUS } from '@/constants'
import StatusTag from '@/components/StatusTag.vue'
import { prettyJson, formatDate } from '@/utils'
import { MagicStick } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const itemId = computed(() => Number(route.params.itemId))

const data = ref<AnnotationItemResponse | null>(null)
const schema = ref<TemplateSchema>({ materials: [] })
const rawData = ref<Record<string, any>>({})
const result = ref<Record<string, any>>({})
const rendererRef = ref<InstanceType<typeof MaterialRenderer>>()
const transitions = ref<any[]>([])
const myItems = ref<TaskItem[]>([])
const totalMyItems = ref(0)
const currentIndex = ref(0)

const loading = ref(false)
const submitting = ref(false)
const drafting = ref(false)

const suggestionId = ref<string | null>(null)
const suggestionStatus = ref<string>('')
const suggestion = ref<any>(null)
const suggestionLoading = ref(false)
let pollTimer: any = null

async function load() {
  loading.value = true
  try {
    const res = await getAnnotationItem(itemId.value)
    data.value = res
    schema.value = res.template_schema || { materials: [] }
    rawData.value = res.raw_data || {}
    result.value = res.result || {}
    transitions.value = res.transitions || []
    for (const m of schema.value.materials) {
      if (m.type === 'text_display' && rawData.value[m.fieldKey] !== undefined) {
        if (result.value[m.fieldKey] === undefined) {
          result.value[m.fieldKey] = rawData.value[m.fieldKey]
        }
      }
    }
    suggestion.value = res.suggestion || null
    myItems.value = (res.my_items || []).map((i: any) => ({ id: i.id, status: i.status, index: i.index } as TaskItem))
    transitions.value = res.transitions || []
  } finally {
    loading.value = false
  }
}

async function handleDraft() {
  rendererRef.value?.sync()
  drafting.value = true
  try {
    await saveDraft(itemId.value, result.value)
    ElMessage.success('草稿已保存')
  } finally {
    drafting.value = false
  }
}

async function handleSubmit() {
  const ok = await rendererRef.value?.validate()
  if (!ok) return
  await ElMessageBox.confirm('确认提交标注结果？', '提交', { type: 'info' }).catch(() => null)
  submitting.value = true
  try {
    await submitItem(itemId.value, result.value)
    ElMessage.success('已提交')
    await load()
  } finally {
    submitting.value = false
  }
}

const taskItem = computed(() => data.value?.item as TaskItem | undefined)

async function generateSuggestion() {
  if (!schema.value.materials.length) { ElMessage.warning('无字段无法生成建议'); return }
  suggestionLoading.value = true
  try {
    const res = await requestSuggestion(itemId.value)
    suggestionId.value = res.suggestion_id
    suggestionStatus.value = 'generating'
    startPolling()
  } catch {
    suggestionLoading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!suggestionId.value) return
    try {
      const res = await getSuggestion(suggestionId.value)
      suggestionStatus.value = res.status
      if (res.status === 'done' && res.suggestion) {
        suggestion.value = res.suggestion
        suggestionLoading.value = false
        stopPolling()
      } else if (res.status === 'error') {
        suggestionLoading.value = false
        stopPolling()
      } else {
        suggestion.value = res.suggestion
      }
    } catch {
      stopPolling()
      suggestionLoading.value = false
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function acceptSuggestion() {
  if (!suggestion.value) return
  const s = typeof suggestion.value === 'string' ? safeParse(suggestion.value) : suggestion.value
  if (s && typeof s === 'object') {
    result.value = { ...result.value, ...s }
    ElMessage.success('已应用 AI 建议到表单')
  } else {
    ElMessage.warning('AI 建议格式无法直接应用')
  }
}

function safeParse(s: string) { try { return JSON.parse(s) } catch { return null } }

function navigateToItem(id: number) {
  router.push(`/workbench/${id}`)
}

onMounted(load)
onUnmounted(stopPolling)
</script>

<template>
  <div class="page" v-loading="loading">
    <PageHeader title="标注工作台" :subtitle="`标注项 #${itemId}`" />

    <div class="workbench-layout">
      <!-- 左侧：任务项导航 -->
      <div class="panel left-panel">
        <div class="panel-header">
          <span>我的标注项</span>
          <span class="panel-count">{{ myItems.length }}</span>
        </div>
        <div class="panel-body">
          <div class="item-nav-list">
            <div
              v-for="it in myItems" :key="it.id"
              class="nav-item"
              :class="{ active: it.id === itemId }"
              @click="navigateToItem(it.id)"
            >
              <span class="nav-index">#{{ it.index + 1 }}</span>
              <StatusTag :status="it.status" size="small" />
            </div>
            <EmptyState v-if="!myItems.length" icon="List" title="暂无项" description="尚无已领取的标注项" />
          </div>
        </div>
      </div>

      <!-- 中间：标注主界面 -->
      <div class="panel center-panel">
        <div class="card">
          <div class="card-header">原始数据</div>
          <div class="card-body">
            <pre class="raw">{{ prettyJson(rawData) }}</pre>
          </div>
        </div>

        <div class="card" style="margin-top: 16px;">
          <div class="card-header">
            <span>标注表单</span>
            <el-button size="small" type="primary" :loading="suggestionLoading" @click="generateSuggestion">
              <el-icon><MagicStick /></el-icon>
              AI 建议
            </el-button>
          </div>
          <div class="card-body">
            <MaterialRenderer ref="rendererRef" :schema="schema" v-model="result" />

            <!-- AI 建议展示 -->
            <div v-if="suggestion" class="ai-suggestion-bar">
              <el-alert type="success" :closable="false" show-icon>
                <template #title>
                  <div class="ai-suggestion-header">
                    <span>AI 建议已生成</span>
                    <div class="ai-suggestion-actions">
                      <el-button size="small" type="success" @click="acceptSuggestion">采纳建议</el-button>
                      <el-button size="small" @click="generateSuggestion">重新生成</el-button>
                    </div>
                  </div>
                </template>
                <pre class="raw sm">{{ prettyJson(suggestion) }}</pre>
              </el-alert>
            </div>
            <div v-if="suggestionLoading" class="ai-suggestion-bar">
              <el-alert type="info" :closable="false" show-icon>
                <template #title>AI 建议生成中<span v-if="suggestionStatus"> ({{ suggestionStatus }})</span>...</template>
              </el-alert>
            </div>

            <div class="form-actions">
              <el-button :loading="drafting" @click="handleDraft">保存草稿</el-button>
              <el-button type="primary" :loading="submitting" @click="handleSubmit">提交</el-button>
            </div>
            <el-alert v-if="taskItem?.status === 'ai_reviewing'" title="已提交 AI 预审中" type="warning" :closable="false" style="margin-top:12px" />
          </div>
        </div>
      </div>

      <!-- 右侧：进度与时间线 -->
      <div class="panel right-panel">
        <div class="card">
          <div class="card-header">标注进度</div>
          <div class="card-body">
            <div class="progress-summary">
              <div class="stat-item">
                <span class="stat-val">{{ myItems.filter(i => i.status === 'approved' || i.status === 'completed').length }}</span>
                <span class="stat-lbl">已完成</span>
              </div>
              <div class="stat-item">
                <span class="stat-val">{{ myItems.filter(i => i.status === 'pending').length }}</span>
                <span class="stat-lbl">待处理</span>
              </div>
              <div class="stat-item">
                <span class="stat-val">{{ taskItem ? TASK_ITEM_STATUS[taskItem.status]?.label : '-' }}</span>
                <span class="stat-lbl">当前状态</span>
              </div>
            </div>
          </div>
        </div>

        <div class="card" style="margin-top: 16px;">
          <div class="card-header">流转时间线</div>
          <div class="card-body">
            <div class="timeline">
              <div v-if="!transitions.length" class="empty-timeline">暂无记录</div>
              <div v-for="tr in transitions.slice().reverse()" :key="tr.id" class="timeline-item">
                <div class="tl-dot" :class="tr.to_status" />
                <div class="tl-content">
                  <div class="tl-status">{{ TASK_ITEM_STATUS[tr.to_status as keyof typeof TASK_ITEM_STATUS]?.label || tr.to_status }}</div>
                  <div class="tl-time">{{ formatDate(tr.created_at) }}</div>
                  <div v-if="tr.comment" class="tl-comment">{{ tr.comment }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.workbench-layout {
  margin-top: 16px;
  display: grid;
  grid-template-columns: 260px 1fr 320px;
  gap: 16px;
  align-items: start;
}
.panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #fff;
  border-bottom: 1px solid var(--lh-border);
  border-radius: 12px 12px 0 0;
  font-weight: 600;
  color: var(--lh-text);
}
.panel-count {
  font-size: 14px;
  color: var(--lh-text-soft);
  font-weight: 500;
}
.panel-body {
  background: #fff;
  border-radius: 0 0 12px 12px;
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.left-panel .panel-body {
  padding: 12px;
}
.card {
  background: #fff;
  border-radius: 12px;
  border: 1px solid var(--lh-border);
  overflow: hidden;
}
.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--lh-border);
  font-weight: 600;
  color: var(--lh-text);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-body {
  padding: 20px;
}
.center-panel {
  overflow-y: auto;
  padding-right: 4px;
  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-thumb {
    background: var(--lh-border);
    border-radius: 3px;
  }
}
.item-nav-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.nav-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border: 1px solid var(--lh-border);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  &:hover {
    border-color: #cbd5e1;
    background: #f8fafc;
  }
}
.nav-item.active {
  border-color: var(--lh-primary);
  background: var(--lh-primary-light);
}
.nav-index {
  font-weight: 600;
  color: var(--lh-text);
  font-size: 14px;
}
.raw {
  background: #f8fafc;
  padding: 16px;
  border-radius: 10px;
  font-size: 12px;
  max-height: 220px;
  overflow: auto;
  margin: 0;
  color: var(--lh-text);
}
.raw.sm {
  max-height: 180px;
}
.ai-suggestion-bar {
  margin-top: 16px;
}
.ai-suggestion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ai-suggestion-actions {
  display: flex;
  gap: 8px;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
.progress-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--lh-border);
}
.stat-val {
  font-weight: 700;
  font-size: 20px;
  color: var(--lh-text);
  letter-spacing: -0.5px;
}
.stat-lbl {
  font-size: 13px;
  color: var(--lh-text-soft);
}
.timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.empty-timeline {
  color: var(--lh-text-soft);
  font-size: 13px;
  text-align: center;
  padding: 20px;
}
.timeline-item {
  display: flex;
  gap: 12px;
}
.tl-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
  background: #cbd5e1;
}
.tl-dot.approved, .tl-dot.completed {
  background: var(--lh-success);
}
.tl-dot.rejected {
  background: var(--lh-danger);
}
.tl-dot.submitted, .tl-dot.reviewed {
  background: var(--lh-primary);
}
.tl-dot.annotating, .tl-dot.ai_reviewing {
  background: var(--lh-warning);
}
.tl-content {
  flex: 1;
}
.tl-status {
  font-weight: 600;
  font-size: 14px;
  color: var(--lh-text);
}
.tl-time {
  font-size: 12px;
  color: var(--lh-text-soft);
  margin-top: 2px;
}
.tl-comment {
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
  line-height: 1.5;
}
</style>
