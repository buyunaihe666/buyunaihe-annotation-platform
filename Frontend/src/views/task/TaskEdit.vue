<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listTemplates, listDatasets, createTask, updateTask, getTask } from '@/api'
import type { Template, Dataset, Task } from '@/types'
import PageHeader from '@/components/PageHeader.vue'

const router = useRouter()
const route = useRoute()
const id = computed(() => (route.params.id ? Number(route.params.id) : undefined))

const templates = ref<Template[]>([])
const datasets = ref<Dataset[]>([])
const form = reactive({
  name: '',
  description: '',
  template_id: undefined as number | undefined,
  dataset_id: undefined as number | undefined,
  enable_ai_audit: true,
  enable_ai_suggestion: true
})

async function loadOptions() {
  templates.value = await listTemplates({ status: 'published' })
  datasets.value = await listDatasets()
}

async function loadTask() {
  if (!id.value) return
  const t: Task = await getTask(id.value)
  form.name = t.name
  form.description = t.description || ''
  form.template_id = t.template_id
  form.dataset_id = t.dataset_id
  form.enable_ai_audit = !!t.enable_ai_audit
  form.enable_ai_suggestion = !!t.enable_ai_suggestion
}

async function submit() {
  if (!form.name) { ElMessage.warning('请填写任务名称'); return }
  if (!form.template_id) { ElMessage.warning('请选择模板'); return }
  if (!form.dataset_id) { ElMessage.warning('请选择数据集'); return }
  const payload = {
    name: form.name,
    description: form.description,
    template_id: form.template_id,
    dataset_id: form.dataset_id,
    enable_ai_audit: form.enable_ai_audit,
    enable_ai_suggestion: form.enable_ai_suggestion
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
  router.replace(`/tasks/${savedId}`)
}

onMounted(async () => {
  await loadOptions()
  if (id.value) await loadTask()
})
</script>

<template>
  <div class="page">
    <PageHeader :title="id ? '编辑任务' : '新建任务'" :subtitle="id ? `任务 ID: ${id}` : '绑定模板与数据集'" />
    <el-card shadow="never" style="max-width:780px">
      <el-form :model="form" label-position="top">
        <el-form-item label="任务名称" required><el-input v-model="form.name" placeholder="如：电商评论情感标注" /></el-form-item>
        <el-form-item label="任务描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="标注模板" required>
              <el-select v-model="form.template_id" placeholder="选择已发布模板" style="width:100%">
                <el-option v-for="t in templates" :key="t.id" :label="`${t.name} (${t.id})`" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据集" required>
              <el-select v-model="form.dataset_id" placeholder="选择数据集" style="width:100%">
                <el-option v-for="d in datasets" :key="d.id" :label="`${d.name} (${d.item_count || 0} 条)`" :value="d.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="AI 能力">
          <div style="display:flex;gap:32px">
            <el-switch v-model="form.enable_ai_suggestion" active-text="AI 标注建议" />
            <el-switch v-model="form.enable_ai_audit" active-text="AI 预审核" />
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="submit">保存</el-button>
          <el-button @click="router.back()">返回</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>