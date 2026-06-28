<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listTemplates, listDatasets, createTask, updateTask, getTask, listUsers } from '@/api'
import type { Template, Dataset, Task, User } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import { Tickets, UserFilled, ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const id = computed(() => (route.params.id ? Number(route.params.id) : undefined))

const templates = ref<Template[]>([])
const datasets = ref<Dataset[]>([])
const users = ref<User[]>([])
const labelers = computed(() => users.value.filter(u => u.role_code === 'labeler'))
const reviewers = computed(() => users.value.filter(u => u.role_code === 'reviewer'))

// ========== 第一部分：基础信息 ==========
const form = reactive({
  name: '',
  description: '',
})

// ========== 第二部分：资源配置 ==========
const resource = reactive({
  template_id: undefined as number | undefined,
  dataset_id: undefined as number | undefined,
  quota: 0,
  max_item_count: 0,
  deadline: '' as string,
  reward_per_item: 0,
  reward_bonus: 0,
})

watch(() => resource.dataset_id, (did) => {
  if (!did) return
  const ds = datasets.value.find(d => d.id === did)
  if (ds) {
    resource.max_item_count = ds.item_count || 0
    if (!resource.quota || resource.quota > resource.max_item_count) {
      resource.quota = resource.max_item_count
    }
  }
})

// ========== 第三部分：分类与分发 ==========
const distribution = reactive({
  tags: [] as string[],
  tagInput: '',
  distribution_type: 'first_come_first_serve' as string,
  assigned_labelers: [] as number[],
  reviewer_chain: [] as number[],  // 审核链路: 按顺序排列的审核员ID
})
const currentReviewer = ref<number>()

function addTag() {
  const t = distribution.tagInput.trim()
  if (t && !distribution.tags.includes(t)) {
    distribution.tags.push(t)
  }
  distribution.tagInput = ''
}
function removeTag(idx: number) {
  distribution.tags.splice(idx, 1)
}
function addReviewer(uid: number) {
  if (uid && !distribution.reviewer_chain.includes(uid)) {
    distribution.reviewer_chain.push(uid)
  }
  currentReviewer.value = undefined
}

// ========== 第四部分：AI 预审配置 ==========
const aiConfig = reactive({
  enable_ai_audit: true,
  enable_ai_suggestion: true,
  audit_prompt: '请根据标注规范审核以下标注结果，检查准确性、完整性和一致性。',
  pass_score: 80,
  review_score: 60,
  dimensions: [
    { name: '准确性', weight: 0.5 },
    { name: '完整性', weight: 0.3 },
    { name: '一致性', weight: 0.2 },
  ],
})

function addDimension() {
  aiConfig.dimensions.push({ name: '', weight: 0 })
}
function removeDimension(idx: number) {
  aiConfig.dimensions.splice(idx, 1)
}

async function loadOptions() {
  templates.value = await listTemplates({ status: 'published' })
  datasets.value = await listDatasets()
  users.value = await listUsers()
}

async function loadTask() {
  if (!id.value) return
  const t: Task = await getTask(id.value)
  form.name = t.name
  form.description = t.description || ''
  resource.template_id = t.template_id
  resource.dataset_id = t.dataset_id
  resource.quota = t.quota || 0
  resource.max_item_count = t.max_item_count || 0
  resource.deadline = t.deadline || ''
  resource.reward_per_item = t.reward_rules?.per_item || 0
  resource.reward_bonus = t.reward_rules?.bonus_approved || 0
  distribution.tags = t.tags || []
  distribution.distribution_type = t.distribution_type || 'first_come_first_serve'
  distribution.reviewer_chain = []
  distribution.assigned_labelers = []
  aiConfig.enable_ai_audit = !!t.enable_ai_audit
  aiConfig.enable_ai_suggestion = !!t.enable_ai_suggestion
  aiConfig.audit_prompt = t.ai_audit_config?.audit_prompt || ''
  aiConfig.pass_score = t.ai_audit_config?.pass_score || 80
  aiConfig.review_score = t.ai_audit_config?.review_score || 60
  aiConfig.dimensions = t.ai_audit_config?.dimensions || [
    { name: '准确性', weight: 0.5 },
    { name: '完整性', weight: 0.3 },
    { name: '一致性', weight: 0.2 },
  ]
}

async function submit() {
  if (!form.name) { ElMessage.warning('请填写任务名称'); return }
  if (!resource.template_id) { ElMessage.warning('请选择标注模板'); return }
  if (!resource.dataset_id) { ElMessage.warning('请选择数据集'); return }
  if (!distribution.reviewer_chain.length) { ElMessage.warning('请配置至少一个审核员'); return }

  const payload = {
    name: form.name,
    description: form.description,
    template_id: resource.template_id,
    dataset_id: resource.dataset_id,
    quota: resource.quota,
    deadline: resource.deadline ? new Date(resource.deadline).toISOString() : null,
    reward_rules: {
      per_item: resource.reward_per_item,
      bonus_approved: resource.reward_bonus,
    },
    tags: distribution.tags,
    distribution_type: distribution.distribution_type,
    enable_ai_audit: aiConfig.enable_ai_audit,
    enable_ai_suggestion: aiConfig.enable_ai_suggestion,
    ai_audit_config: {
      audit_prompt: aiConfig.audit_prompt,
      pass_score: aiConfig.pass_score,
      review_score: aiConfig.review_score,
      dimensions: aiConfig.dimensions.filter(d => d.name && d.weight > 0),
    },
  }

  let savedId: number
  if (id.value) {
    await updateTask(id.value, payload)
    savedId = id.value
    ElMessage.success('已更新')
  } else {
    const t = await createTask(payload)
    savedId = t.id
    ElMessage.success('已创建')
  }

  // 分配人员（包含审核链路）
  const assignments: { user_id: number; role: string; review_order: number }[] = []
  if (distribution.distribution_type === 'assigned') {
    for (const uid of distribution.assigned_labelers) {
      assignments.push({ user_id: uid, role: 'labeler', review_order: 0 })
    }
  }
  distribution.reviewer_chain.forEach((uid, idx) => {
    assignments.push({ user_id: uid, role: 'reviewer', review_order: idx + 1 })
  })
  if (assignments.length) {
    const { assignTask } = await import('@/api')
    await assignTask(savedId, assignments)
  }

  router.replace(`/tasks/${savedId}`)
}

onMounted(async () => {
  await loadOptions()
  if (id.value) await loadTask()
  else {
    // 默认配额为最大
    resource.quota = resource.max_item_count
  }
})
</script>

<template>
  <div class="page">
    <PageHeader :title="id ? '编辑任务' : '新建任务'" :subtitle="id ? `任务 ID: ${id}` : '四个步骤完成任务配置'" />

    <el-steps :active="1" simple style="margin-bottom:20px">
      <el-step title="基础信息" icon="Edit" />
      <el-step title="资源配置" icon="Setting" />
      <el-step title="分类与分发" icon="Share" />
      <el-step title="AI 预审" icon="MagicStick" />
    </el-steps>

    <el-form label-position="top">
      <!-- 第一部分：基础信息 -->
      <el-card shadow="never" style="margin-bottom:16px">
        <template #header><span style="font-weight:600">第一部分 · 基础信息</span></template>
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="任务名称" required>
              <el-input v-model="form.name" placeholder="如：电商评论情感标注任务" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="任务描述">
              <el-input v-model="form.description" placeholder="任务用途和说明" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-card>

      <!-- 第二部分：资源配置 -->
      <el-card shadow="never" style="margin-bottom:16px">
        <template #header><span style="font-weight:600">第二部分 · 资源配置</span></template>
        <el-row :gutter="24">
          <el-col :span="8">
            <el-form-item label="标注模板" required>
              <el-select v-model="resource.template_id" placeholder="选择已发布模板" style="width:100%">
                <el-option v-for="t in templates" :key="t.id" :label="`${t.name} (ID:${t.id})`" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="数据集" required>
              <el-select v-model="resource.dataset_id" placeholder="选择数据集" style="width:100%">
                <el-option v-for="d in datasets" :key="d.id" :label="`${d.name} (${d.item_count || 0} 条)`" :value="d.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="任务配额" required>
              <el-input-number v-model="resource.quota" :min="0" :max="resource.max_item_count || 999999" style="width:100%" />
              <div style="color:#8a93a6;font-size:12px;margin-top:4px">最大不能超过数据集总量：{{ resource.max_item_count }}</div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="24">
          <el-col :span="8">
            <el-form-item label="截止时间">
              <el-date-picker v-model="resource.deadline" type="datetime" placeholder="选择截止时间" style="width:100%" value-format="YYYY-MM-DDTHH:mm:ss" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="每条奖励 (元)">
              <el-input-number v-model="resource.reward_per_item" :min="0" :step="0.1" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="通过额外奖励 (元)">
              <el-input-number v-model="resource.reward_bonus" :min="0" :step="0.1" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-card>

      <!-- 第三部分：分类与分发配置 -->
      <el-card class="section-card" style="margin-bottom:16px">
        <template #header><span class="section-title">第三部分 · 分类与分发配置</span></template>
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="任务标签">
              <div class="tag-container">
                <el-tag v-for="(tag, idx) in distribution.tags" :key="idx" closable @close="removeTag(idx)" class="task-tag">
                  {{ tag }}
                </el-tag>
              </div>
              <div class="tag-input-row">
                <el-input v-model="distribution.tagInput" placeholder="输入标签后回车添加" @keyup.enter="addTag" />
                <el-button type="primary" @click="addTag">添加</el-button>
              </div>
              <div class="form-hint">标注员可在任务广场通过标签搜索</div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="任务分配方式">
              <div class="distribution-options">
                <div 
                  class="distribution-option" 
                  :class="{ active: distribution.distribution_type === 'first_come_first_serve' }"
                  @click="distribution.distribution_type = 'first_come_first_serve'"
                >
                  <div class="option-icon">
                    <el-icon :size="28"><Tickets /></el-icon>
                  </div>
                  <div class="option-content">
                    <div class="option-title">先到先得</div>
                    <div class="option-desc">标注人员在任务广场领取任务配额</div>
                  </div>
                  <div class="option-radio">
                    <el-radio :model-value="distribution.distribution_type === 'first_come_first_serve'" />
                  </div>
                </div>
                <div 
                  class="distribution-option" 
                  :class="{ active: distribution.distribution_type === 'assigned' }"
                  @click="distribution.distribution_type = 'assigned'"
                >
                  <div class="option-icon">
                    <el-icon :size="28"><UserFilled /></el-icon>
                  </div>
                  <div class="option-content">
                    <div class="option-title">指派</div>
                    <div class="option-desc">指定标注员平分任务配额</div>
                  </div>
                  <div class="option-radio">
                    <el-radio :model-value="distribution.distribution_type === 'assigned'" />
                  </div>
                </div>
              </div>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 指派标注员 -->
        <div v-if="distribution.distribution_type === 'assigned'" class="assign-section">
          <div class="assign-label">指派标注员</div>
          <el-select v-model="distribution.assigned_labelers" multiple placeholder="选择标注员" style="width:100%">
            <el-option v-for="u in labelers" :key="u.id" :label="`${u.nickname || u.username}`" :value="u.id" />
          </el-select>
        </div>

        <!-- 审核链路 -->
        <div class="review-chain-section">
          <div class="review-chain-label">审核链路</div>
          <div class="review-chain-tags">
            <div v-for="(uid, idx) in distribution.reviewer_chain" :key="uid" class="reviewer-tag-wrapper">
              <el-tag type="success" closable @close="distribution.reviewer_chain.splice(idx, 1)" class="reviewer-tag">
                <span class="reviewer-order">#{{ idx + 1 }}</span>
                <span class="reviewer-name">{{ reviewers.find(u => u.id === uid)?.nickname || uid }}</span>
              </el-tag>
              <el-icon v-if="idx < distribution.reviewer_chain.length - 1" class="chain-arrow"><ArrowRight /></el-icon>
            </div>
          </div>
          <div class="reviewer-select-row">
            <el-select v-model="currentReviewer" placeholder="选择审核员添加到链路" style="width:300px" @change="addReviewer">
              <el-option v-for="u in reviewers.filter(ru => !distribution.reviewer_chain.includes(ru.id))" :key="u.id" :label="`${u.nickname || u.username}`" :value="u.id" />
            </el-select>
            <span v-if="distribution.reviewer_chain.length" class="review-hint">
              共 {{ distribution.reviewer_chain.length }} 级审核，末端审核员通过后任务完成
            </span>
          </div>
        </div>
      </el-card>

      <!-- 第四部分：AI 预审配置 -->
      <el-card shadow="never" style="margin-bottom:16px">
        <template #header><span style="font-weight:600">第四部分 · AI 预审配置</span></template>
        <el-row :gutter="24">
          <el-col :span="12">
            <el-form-item label="AI 能力开关">
              <div style="display:flex;gap:32px">
                <el-switch v-model="aiConfig.enable_ai_suggestion" active-text="AI 标注建议" />
                <el-switch v-model="aiConfig.enable_ai_audit" active-text="AI 预审核" />
              </div>
            </el-form-item>
            <el-form-item v-if="aiConfig.enable_ai_audit" label="审核提示词">
              <el-input v-model="aiConfig.audit_prompt" type="textarea" :rows="4" placeholder="AI 预审的审核提示词" />
            </el-form-item>
          </el-col>
          <el-col v-if="aiConfig.enable_ai_audit" :span="12">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="通过分数 (>=)">
                  <el-input-number v-model="aiConfig.pass_score" :min="0" :max="100" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="需人工评审分数 (<)">
                  <el-input-number v-model="aiConfig.review_score" :min="0" :max="100" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="维度权重配置">
              <div v-for="(dim, idx) in aiConfig.dimensions" :key="idx" style="display:flex;gap:8px;margin-bottom:8px;align-items:center">
                <el-input v-model="dim.name" placeholder="维度名称" style="width:160px" />
                <el-input-number v-model="dim.weight" :min="0" :max="1" :step="0.05" :precision="2" style="width:140px" />
                <span style="color:#8a93a6;font-size:12px">权重</span>
                <el-button size="small" type="danger" @click="removeDimension(idx)">删除</el-button>
              </div>
              <el-button size="small" @click="addDimension">添加维度</el-button>
              <div v-if="aiConfig.dimensions.length" style="margin-top:6px;font-size:12px;color:#8a93a6">
                权重合计：{{ aiConfig.dimensions.reduce((s, d) => s + (d.weight || 0), 0).toFixed(2) }}
              </div>
            </el-form-item>
          </el-col>
        </el-row>
      </el-card>

      <div style="display:flex;gap:12px">
        <el-button type="primary" size="large" @click="submit">
          {{ id ? '保存修改' : '创建任务' }}
        </el-button>
        <el-button @click="router.back()">返回</el-button>
      </div>
    </el-form>
  </div>
</template>

<style scoped lang="scss">
.section-card {
  border-radius: 12px;
  border: 1px solid var(--lh-border);
  :deep(.el-card__header) {
    border-bottom: 1px solid var(--lh-border);
    padding: 16px 20px;
  }
}

.section-title {
  font-weight: 600;
  color: var(--lh-text);
  font-size: 15px;
}

.tag-container {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  min-height: 36px;
}

.task-tag {
  border-radius: 8px;
  padding: 4px 12px;
}

.tag-input-row {
  display: flex;
  gap: 8px;
}

.form-hint {
  font-size: 12px;
  color: var(--lh-text-soft);
  margin-top: 6px;
}

.distribution-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.distribution-option {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border: 2px solid var(--lh-border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fff;

  &:hover {
    border-color: #cbd5e1;
    background: #f8fafc;
  }

  &.active {
    border-color: var(--lh-primary);
    background: var(--lh-primary-light);
  }
}

.option-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--lh-primary);
  flex-shrink: 0;
}

.distribution-option.active .option-icon {
  background: var(--lh-primary);
  color: white;
}

.option-content {
  flex: 1;
}

.option-title {
  font-weight: 600;
  font-size: 15px;
  color: var(--lh-text);
  margin-bottom: 4px;
}

.option-desc {
  font-size: 13px;
  color: var(--lh-text-soft);
}

.assign-section,
.review-chain-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--lh-border);
}

.assign-label,
.review-chain-label {
  font-weight: 500;
  color: var(--lh-text);
  font-size: 14px;
  margin-bottom: 10px;
}

.review-chain-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  min-height: 40px;
}

.reviewer-tag-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
}

.reviewer-tag {
  border-radius: 8px;
  padding: 6px 14px;
  display: flex;
  gap: 6px;
  align-items: center;
}

.reviewer-order {
  font-weight: 600;
  font-size: 12px;
  opacity: 0.9;
}

.reviewer-name {
  font-size: 13px;
}

.chain-arrow {
  color: #cbd5e1;
  font-size: 16px;
}

.reviewer-select-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.review-hint {
  font-size: 12px;
  color: var(--lh-text-soft);
}
</style>
