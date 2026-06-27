<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getReviewItem, getReviewAiReport, submitDecision } from '@/api'
import type { ReviewItemResponse, AiReport, TemplateSchema } from '@/types'
import MaterialView from '@/components/MaterialView.vue'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { prettyJson } from '@/utils'

const route = useRoute()
const router = useRouter()
const itemId = computed(() => Number(route.params.itemId))

const data = ref<ReviewItemResponse | null>(null)
const schema = ref<TemplateSchema>({ materials: [] })
const rawData = ref<Record<string, any>>({})
const result = ref<Record<string, any> | null>(null)
const aiReport = ref<AiReport | null>(null)
const aiLoading = ref(false)

const decision = ref<'approved' | 'rejected' | 'modify_approve'>('approved')
const comment = ref('')
const deciding = ref(false)
let pollTimer: any = null

async function load() {
  const res = await getReviewItem(itemId.value)
  data.value = res
  schema.value = res.template_schema || { materials: [] }
  rawData.value = res.raw_data || {}
  result.value = res.result || null
  aiReport.value = res.ai_report || null
  if (!aiReport.value || aiReport.value.status === 'processing' || aiReport.value.status === 'pending') {
    pollAiReport()
  }
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
    if (status === 'done' || status === 'error') {
      aiLoading.value = false
      stopPolling()
    }
  }, 2500)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function submitReview() {
  if (!comment.value && decision.value !== 'approved') {
    await ElMessageBox.confirm('确认不填写评论直接提交？', '提示', { type: 'warning' }).catch(() => null)
  }
  deciding.value = true
  try {
    await submitDecision(itemId.value, decision.value, comment.value)
    ElMessage.success('审核已提交')
    router.back()
  } finally {
    deciding.value = false
  }
}

onMounted(() => { load().catch(() => {}) })
onUnmounted(stopPolling)

const scoreColor = computed(() => {
  const s = aiReport.value?.score
  if (s === undefined || s === null) return '#1f2430'
  if (s >= 80) return '#52c41a'
  if (s >= 60) return '#f5a623'
  return '#ec4747'
})
</script>

<template>
  <div class="page">
    <PageHeader title="审核工作台" :subtitle="`审核项 #${itemId}`" />
    <el-button @click="router.back()">返回</el-button>

    <el-row :gutter="16" style="margin-top:12px">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>原始数据</template>
          <pre class="raw">{{ prettyJson(rawData) }}</pre>
        </el-card>

        <el-card shadow="never" style="margin-top:16px">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>标注结果</span>
              <el-tag v-if="data?.item" size="small" effect="plain">{{ data.item.status }}</el-tag>
            </div>
          </template>
          <MaterialView :schema="schema" :result="result" />
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>AI 预审核报告</span>
              <el-button v-if="aiReport?.status === 'error' || !aiReport" size="small" @click="pollAiReport">刷新</el-button>
            </div>
          </template>
          <div v-if="aiLoading" style="padding:20px;text-align:center">
            <el-progress :indeterminate="true" :percentage="50" />
            <div style="color:#8a93a6;margin-top:8px">AI 报告生成中...</div>
          </div>
          <div v-else-if="aiReport && aiReport.status === 'done'">
            <div class="score-box">
              <div class="score" :style="{ color: scoreColor }">{{ aiReport.score ?? '-' }}</div>
              <div class="l">综合评分</div>
            </div>
            <el-descriptions v-if="aiReport.issues?.length" :column="1" border style="margin-top:12px">
              <el-descriptions-item label="问题列表">
                <ul style="margin:0;padding-left:18px"><li v-for="(i, idx) in aiReport.issues" :key="idx">{{ i }}</li></ul>
              </el-descriptions-item>
              <el-descriptions-item label="模型">{{ aiReport.model || 'rule-based' }}</el-descriptions-item>
            </el-descriptions>
            <el-divider content-position="left">审核推理</el-divider>
            <div class="reasoning">{{ aiReport.reasoning || '无' }}</div>
            <el-divider content-position="left">修改建议</el-divider>
            <div class="reasoning">{{ aiReport.suggestion || '无' }}</div>
          </div>
          <div v-else-if="aiReport?.status === 'error'">
            <el-alert :title="aiReport.error || 'AI 报告生成失败'" type="error" :closable="false" />
          </div>
          <EmptyState v-else icon="MagicStick" title="无 AI 报告" description="该任务未启用 AI 预审核" />
        </el-card>

        <el-card shadow="never" style="margin-top:16px">
          <template #header>审核决策</template>
          <el-form label-position="top">
            <el-form-item label="决策结果">
              <el-radio-group v-model="decision">
                <el-radio label="approved">通过</el-radio>
                <el-radio label="rejected">驳回</el-radio>
                <el-radio label="modify_approve">修改后通过</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="审核意见">
              <el-input v-model="comment" type="textarea" :rows="3" placeholder="请填写审核意见" />
            </el-form-item>
            <el-button type="primary" :loading="deciding" @click="submitReview">提交审核</el-button>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.raw { background:#f6f8fa; padding:12px; border-radius:8px; font-size:12px; max-height:240px; overflow:auto; margin:0; }
.score-box { text-align:center; padding:10px 0; }
.score-box .score { font-size:48px; font-weight:700; line-height:1; }
.score-box .l { color:#8a93a6; font-size:13px; margin-top:4px; }
.reasoning { white-space:pre-wrap; color:#1f2430; font-size:13px; line-height:1.7; }
</style>