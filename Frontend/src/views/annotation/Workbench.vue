<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAnnotationItem, saveDraft, submitItem, requestSuggestion, getSuggestion } from '@/api'
import type { AnnotationItemResponse, TemplateSchema } from '@/types'
import MaterialRenderer from '@/components/MaterialRenderer.vue'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { prettyJson } from '@/utils'

const route = useRoute()
const router = useRouter()
const itemId = computed(() => Number(route.params.itemId))

const data = ref<AnnotationItemResponse | null>(null)
const schema = ref<TemplateSchema>({ materials: [] })
const rawData = ref<Record<string, any>>({})
const result = ref<Record<string, any>>({})
const rendererRef = ref<InstanceType<typeof MaterialRenderer>>()

const loading = ref(false)
const submitting = ref(false)
const drafting = ref(false)

const aiSuggestionEnabled = computed(() => false)
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
    suggestion.value = res.suggestion || null
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
  await ElMessageBox.confirm(task.value?.enable_ai_audit ? '提交后将触发 AI 预审核，确认提交？' : '确认提交标注结果？', '提交', { type: 'info' }).catch(() => null)
    .then((r: any) => r)
  drafting.value = false
  submitting.value = true
  try {
    await submitItem(itemId.value, result.value)
    ElMessage.success('已提交')
    await load()
  } finally {
    submitting.value = false
  }
}

const task = computed(() => data.value?.item as any)

async function generateSuggestion() {
  if (!schema.value.materials.length) { ElMessage.warning('无字段无法生成建议'); return }
  suggestionLoading.value = true
  try {
    const res = await requestSuggestion(itemId.value)
    suggestionId.value = res.suggestion_id
    suggestionStatus.value = 'generating'
    startPolling()
  } catch (e) {
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

function safeParse(s: string) {
  try { return JSON.parse(s) } catch { return null }
}

onMounted(load)
onUnmounted(stopPolling)

// Auto-poll when ai_reviewing
watch(task, (val) => {
  if (val?.status === 'ai_reviewing') {
    startAuditPolling()
  } else {
    stopPolling()
  }
})

function startAuditPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    await load()
  }, 3000)
}
</script>

<template>
  <div class="page" v-loading="loading">
    <PageHeader title="标注工作台" :subtitle="`标注项 #${itemId}`" />

    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>原始数据</span>
              <div>
                <el-button size="small" @click="router.push('/square')">返回广场</el-button>
              </div>
            </div>
          </template>
          <pre class="raw">{{ prettyJson(rawData) }}</pre>
        </el-card>

        <el-card shadow="never" style="margin-top:16px">
          <template #header>标注表单</template>
          <MaterialRenderer ref="rendererRef" :schema="schema" v-model="result" />
          <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:12px">
            <el-button :loading="drafting" @click="handleDraft">保存草稿</el-button>
            <el-button type="primary" :loading="submitting" @click="handleSubmit">提交</el-button>
          </div>
          <el-alert v-if="task?.status === 'ai_reviewing'" title="AI 预审核进行中，请等待审核完成" type="warning" :closable="false" style="margin-top:10px" />
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>AI 建议</span>
              <el-button size="small" type="primary" :loading="suggestionLoading" @click="generateSuggestion">
                <el-icon style="margin-right:4px"><MagicStick /></el-icon>生成 AI 建议
              </el-button>
            </div>
          </template>
          <div v-if="suggestionLoading" style="padding:20px;text-align:center">
            <el-progress :percentage="suggestionStatus==='generating' ? 60 : 20" :indeterminate="true" />
            <div style="color:#8a93a6;margin-top:8px">{{ suggestionStatus || '生成中' }}...</div>
          </div>
          <div v-else-if="suggestion">
            <div style="margin-bottom:10px">
              <el-tag size="small" type="success" effect="plain">AI 建议可用</el-tag>
            </div>
            <pre class="raw sm">{{ prettyJson(suggestion) }}</pre>
            <el-button type="success" size="small" @click="acceptSuggestion" style="margin-top:10px">应用到表单</el-button>
          </div>
          <EmptyState v-else icon="MagicStick" title="尚无 AI 建议" description="点击「生成 AI 建议」获取智能标注辅助" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.raw { background:#f6f8fa; padding:12px; border-radius:8px; font-size:12px; max-height:240px; overflow:auto; margin:0; }
.raw.sm { max-height: 320px; }
</style>