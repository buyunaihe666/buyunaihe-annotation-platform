<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getReviewItem, getReviewAiReport, submitDecision, submitModifyAndPass, listReviewItems } from '@/api'
import type { ReviewItemResponse, AiReport, TemplateSchema, TaskItem, TaskTransition } from '@/types'
import MaterialView from '@/components/MaterialView.vue'
import MaterialRenderer from '@/components/MaterialRenderer.vue'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import StatusTag from '@/components/StatusTag.vue'
import { TASK_ITEM_STATUS } from '@/constants'
import { prettyJson, formatDate } from '@/utils'

const route = useRoute()
const router = useRouter()
const itemId = computed(() => Number(route.params.itemId))

const data = ref<ReviewItemResponse | null>(null)
const schema = ref<TemplateSchema>({ materials: [] })
const rawData = ref<Record<string, any>>({})
const result = ref<Record<string, any> | null>(null)
const aiReport = ref<AiReport | null>(null)
const transitions = ref<TaskTransition[]>([])
const aiLoading = ref(false)
const reviewItems = ref<TaskItem[]>([])

// 当前项在列表中的位置
const currentListIndex = computed(() => reviewItems.value.findIndex(i => i.id === itemId.value))
const hasNext = computed(() => currentListIndex.value >= 0 && currentListIndex.value < reviewItems.value.length - 1)
const hasPrev = computed(() => currentListIndex.value > 0)

const decision = ref<'approved' | 'rejected' | 'modify_approve'>('approved')
const comment = ref('')
const deciding = ref(false)
const modifyMode = ref(false)
const editableResult = ref<Record<string, any>>({})
const rendererRef = ref<InstanceType<typeof MaterialRenderer>>()
let pollTimer: any = null

async function load() {
  const res = await getReviewItem(itemId.value)
  data.value = res
  schema.value = res.template_schema || { materials: [] }
  rawData.value = res.raw_data || {}
  result.value = res.result || null
  transitions.value = res.transitions || []
  aiReport.value = res.ai_report || null
  editableResult.value = res.result ? JSON.parse(JSON.stringify(res.result)) : {}
  if (!aiReport.value || aiReport.value.status === 'processing' || aiReport.value.status === 'pending') {
    pollAiReport()
  }
  if (data.value?.item?.task_id) {
    await loadReviewItems(data.value.item.task_id)
  }
}

async function loadReviewItems(taskId: number) {
  try {
    const res = await listReviewItems(taskId, { page: 1, size: 100 })
    reviewItems.value = res.items.map((item: any) => ({
      id: item.id,
      index: item.index,
      status: item.status,
      task_id: item.task_id,
    }))
  } catch {
    reviewItems.value = []
  }
}

function navigateToItem(itemId: number) {
  router.push(`/review/workbench/${itemId}`)
}

function goToNext() {
  if (hasNext.value) navigateToItem(reviewItems.value[currentListIndex.value + 1].id)
}

function goToPrev() {
  if (hasPrev.value) navigateToItem(reviewItems.value[currentListIndex.value - 1].id)
}

async function fetchAiReport() {
  try {
    const r = await getReviewAiReport(itemId.value)
    aiReport.value = r
    return r.status
  } catch {
    return 'error'
  }
}

function pollAiReport() {
  aiLoading.value = true
  stopPolling()
  pollTimer = setInterval(async () => {
    const status = await fetchAiReport()
    if (status !== 'processing' && status !== 'pending') {
      aiLoading.value = false
      stopPolling()
    }
  }, 2500)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

function enterModifyMode() {
  modifyMode.value = true
  decision.value = 'modify_approve'
}

async function submitReview() {
  if (!comment.value && decision.value !== 'approved') {
    await ElMessageBox.confirm('确认不填写评论直接提交？', '提示', { type: 'warning' }).catch(() => null)
  }
  deciding.value = true
  try {
    if (decision.value === 'modify_approve') {
      // 修改后通过：提交修改后的结果
      await submitModifyAndPass(itemId.value, {
        decision: 'modify_approve',
        comment: JSON.stringify(editableResult.value),
      })
    } else {
      await submitDecision(itemId.value, decision.value, comment.value)
    }
    ElMessage.success('审核已提交')
    // 自动跳转下一项，没有下一项时返回列表
    if (hasNext.value) {
      goToNext()
    } else {
      router.back()
    }
  } finally {
    deciding.value = false
  }
}

const scoreColor = computed(() => {
  const s = aiReport.value?.score
  if (s === undefined || s === null) return '#1e293b'
  if (s >= 80) return '#10b981'
  if (s >= 60) return '#f59e0b'
  return '#ef4444'
})

watch(itemId, load, { immediate: true })
onUnmounted(stopPolling)
</script>

<template>
  <div class="page">
    <PageHeader title="审核工作台" :subtitle="`审核项 #${itemId}`" />

    <div class="workbench-layout">
      <!-- 左侧：导航 -->
      <div class="panel left-panel">
        <div class="panel-header">待审核项</div>
        <div class="panel-body">
          <div class="item-nav-list">
            <div
              v-for="item in reviewItems"
              :key="item.id"
              class="nav-item"
              :class="{ active: item.id === itemId }"
              @click="navigateToItem(item.id)"
            >
              <span class="nav-index">#{{ item.index }}</span>
              <StatusTag :status="item.status" size="small" />
            </div>
            <EmptyState v-if="!reviewItems.length" icon="List" title="待审项" description="使用列表导航" />
          </div>
        </div>
      </div>

      <!-- 中间：审核内容 -->
      <div class="panel center-panel">
        <div class="card">
          <div class="card-header">原始数据</div>
          <div class="card-body">
            <pre class="raw">{{ prettyJson(rawData) }}</pre>
          </div>
        </div>

        <div class="card" style="margin-top: 16px;">
          <div class="card-header">
            <span>标注结果</span>
            <StatusTag :status="data?.item?.status || ''" />
          </div>
          <div class="card-body">
            <MaterialRenderer v-if="modifyMode" ref="rendererRef" :schema="schema" v-model="editableResult" />
            <MaterialView v-else :schema="schema" :result="result" />
          </div>
        </div>

        <!-- 修改并直接通过 -->
        <div class="card" style="margin-top: 16px;">
          <div class="card-header">
            <div class="header-with-action">
              <span>审核决策</span>
              <el-button size="small" type="warning" plain @click="enterModifyMode">
                修改并直接通过
              </el-button>
            </div>
          </div>
          <div class="card-body">
            <el-form label-position="top">
              <el-form-item label="决策结果">
                <el-radio-group v-model="decision">
                  <el-radio value="approved">通过</el-radio>
                  <el-radio value="rejected">驳回</el-radio>
                  <el-radio value="modify_approve">修改后通过</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="modifyMode" label="提示">
                <el-alert type="warning" :closable="false" show-icon title="修改模式已开启，请在上方标注结果区域直接修改" />
              </el-form-item>
              <el-form-item label="审核意见">
                <el-input v-model="comment" type="textarea" :rows="2" placeholder="填写审核意见或驳回原因" />
              </el-form-item>
              <div class="review-actions">
                <el-button @click="goToPrev" :disabled="!hasPrev">上一项</el-button>
                <el-button type="primary" :loading="deciding" @click="submitReview">提交审核并下一项</el-button>
                <el-button @click="goToNext" :disabled="!hasNext">下一项</el-button>
              </div>
            </el-form>
          </div>
        </div>
      </div>

      <!-- 右侧：AI 预审 + 时间线 -->
      <div class="panel right-panel">
        <div class="card">
          <div class="card-header">
            <span>AI 预审报告</span>
            <el-button v-if="!aiReport || aiReport.status === 'error'" size="small" @click="pollAiReport">刷新</el-button>
          </div>
          <div class="card-body">
            <div v-if="aiLoading" class="ai-loading">
              <el-progress :indeterminate="true" :percentage="50" />
              <div style="color: var(--lh-text-soft); margin-top: 12px;">AI 报告生成中...</div>
            </div>
            <div v-else-if="aiReport && aiReport.status === 'done'">
              <div class="score-box">
                <div class="score" :style="{ color: scoreColor }">{{ aiReport.score ?? '-' }}</div>
                <div class="score-label">综合评分</div>
              </div>
              <!-- 各维度评分 -->
              <div v-if="aiReport.evidence?.dimensions" class="dimensions">
                <div v-for="(dim, idx) in aiReport.evidence.dimensions" :key="idx" class="dim-item">
                  <div class="dim-header">
                    <div class="dim-name">{{ dim.name }}</div>
                    <div class="dim-score" :style="{ color: dim.score >= 80 ? 'var(--lh-success)' : dim.score >= 60 ? 'var(--lh-warning)' : 'var(--lh-danger)' }">{{ dim.score }}</div>
                  </div>
                  <div class="dim-reason">{{ dim.reason }}</div>
                </div>
              </div>
              <el-descriptions v-if="aiReport.issues?.length" :column="1" border style="margin-top: 16px">
                <el-descriptions-item label="问题">
                  <ul style="margin:0;padding-left:18px"><li v-for="(i, idx) in aiReport.issues" :key="idx">{{ i }}</li></ul>
                </el-descriptions-item>
                <el-descriptions-item label="模型">{{ aiReport.model || 'rule-based' }}</el-descriptions-item>
              </el-descriptions>
              <div class="section-divider">审核推理</div>
              <div class="reasoning">{{ aiReport.reasoning || '无' }}</div>
              <div class="section-divider">建议</div>
              <div class="reasoning">{{ aiReport.suggestion || '无' }}</div>
              <div v-if="aiReport.evidence?.total_reason" class="reasoning" style="margin-top: 12px">
                <strong>综合结论：</strong>{{ aiReport.evidence.total_reason }}
              </div>
            </div>
            <div v-else-if="aiReport?.status === 'error'">
              <el-alert title="AI 报告生成失败" type="error" :closable="false" />
            </div>
            <EmptyState v-else icon="MagicStick" title="无 AI 报告" description="该任务未启用 AI 预审核" />
          </div>
        </div>

        <div class="card" style="margin-top: 16px;">
          <div class="card-header">审计时间线</div>
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
  grid-template-columns: 260px 1fr 360px;
  gap: 16px;
  align-items: start;
}
.panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.panel-header {
  padding: 16px 20px;
  background: #fff;
  border-bottom: 1px solid var(--lh-border);
  border-radius: 12px 12px 0 0;
  font-weight: 600;
  color: var(--lh-text);
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
.header-with-action {
  display: flex;
  align-items: center;
  gap: 12px;
}
.card-body {
  padding: 20px;
}
.review-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
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
  transition: all 0.2s;
}
.nav-item:hover {
  border-color: var(--lh-primary);
  background: rgba(var(--lh-primary-rgb), 0.05);
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
.ai-loading {
  text-align: center;
  padding: 30px 20px;
}
.score-box {
  text-align: center;
  padding: 16px 0 20px;
}
.score-box .score {
  font-size: 46px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -1px;
}
.score-box .score-label {
  color: var(--lh-text-soft);
  font-size: 14px;
  margin-top: 6px;
}
.dimensions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 8px;
}
.dim-item {
  background: #f8fafc;
  border-radius: 10px;
  padding: 14px;
}
.dim-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.dim-name {
  font-weight: 600;
  font-size: 14px;
}
.dim-score {
  font-size: 22px;
  font-weight: 700;
}
.dim-reason {
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}
.section-divider {
  margin: 16px 0 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--lh-border);
  font-weight: 600;
  font-size: 14px;
  color: var(--lh-text);
}
.reasoning {
  white-space: pre-wrap;
  color: var(--lh-text);
  font-size: 14px;
  line-height: 1.7;
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
