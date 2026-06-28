<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, defineComponent, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTemplate, createTemplate, updateTemplate, publishTemplate } from '@/api'
import { MATERIAL_TYPES } from '@/constants'
import type { Material, MaterialType, TemplateSchema } from '@/types'
import { genId } from '@/utils'
import PageHeader from '@/components/PageHeader.vue'
import {
  Plus, Delete, Document, DocumentAdd
} from '@element-plus/icons-vue'

const DraggableFree = defineComponent({
  name: 'DraggableFree',
  setup(_, { slots }) { return () => h('div', slots.default?.()) }
})

const router = useRouter()
const route = useRoute()
const id = computed(() => (route.params.id ? Number(route.params.id) : undefined))

const form = reactive<{ name: string; description: string }>({ name: '', description: '' })
const materials = ref<Material[]>([])
const selectedId = ref<string | null>(null)

const selected = computed<Material | undefined>(() => materials.value.find(m => m.id === selectedId.value))

function addMaterial(type: MaterialType) {
  const label = MATERIAL_TYPES.find(t => t.value === type)?.label || type
  const m: Material = {
    id: genId(),
    fieldKey: `field_${materials.value.length + 1}`,
    label,
    type,
    required: false,
    options: type === 'radio' || type === 'checkbox' || type === 'select' ? ['选项A', '选项B'] : undefined,
    props: initProps(type),
    sortOrder: materials.value.length
  }
  materials.value.push(m)
  selectedId.value = m.id
}

function initProps(type: MaterialType): Record<string, any> {
  switch (type) {
    case 'textarea': return { rows: 4 }
    case 'select': return { multiple: false }
    case 'number': return { min: undefined, max: undefined, step: 1 }
    case 'rating': return { max: 5 }
    default: return {}
  }
}

// Ensure props/options are initialized when type changes
watch(() => selected.value?.type, (newType, oldType) => {
  if (!selected.value || newType === oldType) return
  const m = selected.value
  // Reset options for choice types
  if (['radio', 'checkbox', 'select'].includes(newType)) {
    if (!m.options || !m.options.length) m.options = ['选项A', '选项B']
  } else {
    m.options = undefined
  }
  // Initialize props for the new type
  m.props = initProps(newType)
})

function selectMaterial(mid: string) {
  selectedId.value = mid
}

function removeMaterial(mid: string) {
  materials.value = materials.value.filter(m => m.id !== mid)
  if (selectedId.value === mid) selectedId.value = materials.value[0]?.id || null
}

function moveUp(mid: string) {
  const i = materials.value.findIndex(m => m.id === mid)
  if (i > 0) {
    const arr = materials.value
    ;[arr[i - 1], arr[i]] = [arr[i], arr[i - 1]]
    arr.forEach((m, idx) => (m.sortOrder = idx))
  }
}
function moveDown(mid: string) {
  const i = materials.value.findIndex(m => m.id === mid)
  if (i >= 0 && i < materials.value.length - 1) {
    const arr = materials.value
    ;[arr[i + 1], arr[i]] = [arr[i], arr[i + 1]]
    arr.forEach((m, idx) => (m.sortOrder = idx))
  }
}

function addOption(m: Material) {
  m.options = m.options || []
  m.options.push(`选项${m.options.length + 1}`)
}
function removeOption(m: Material, idx: number) {
  m.options?.splice(idx, 1)
}

function fieldKeyCheck(): string | null {
  const seen = new Set<string>()
  for (const m of materials.value) {
    if (!m.fieldKey || !m.fieldKey.trim()) return '存在空的字段标识'
    if (seen.has(m.fieldKey)) return `字段标识重复：${m.fieldKey}`
    seen.add(m.fieldKey)
  }
  return null
}

function buildSchema(): TemplateSchema {
  return { materials: materials.value.map((m, idx) => ({ ...m, sortOrder: idx })) }
}

async function save() {
  if (!form.name) { ElMessage.warning('请填写模板名称'); return }
  if (!materials.value.length) { ElMessage.warning('至少添加一个字段'); return }
  const dup = fieldKeyCheck()
  if (dup) { ElMessage.warning(dup); return }
  const schema = buildSchema()
  if (id.value) {
    await updateTemplate(id.value, { name: form.name, description: form.description, schema })
    ElMessage.success('已保存')
  } else {
    const t = await createTemplate({ name: form.name, description: form.description, schema })
    ElMessage.success('已创建')
    router.replace(`/templates/${t.id}/edit`)
  }
}

async function saveAndPublish() {
  if (!id.value) {
    await save()
  } else {
    await save()
  }
  if (id.value) {
    await publishTemplate(id.value)
    ElMessage.success('已发布')
    load()
  }
}

async function load() {
  if (!id.value) return
  const t = await getTemplate(id.value)
  form.name = t.name
  form.description = t.description || ''
  materials.value = (t.schema?.materials || []).map((m: Material) => ({ ...m }))
  selectedId.value = materials.value[0]?.id || null
}

onMounted(() => {
  if (id.value) load()
  else if (!materials.value.length) addMaterial('text')
})

watch(materials, () => { if (!selectedId.value && materials.value[0]) selectedId.value = materials.value[0].id }, { immediate: true })
</script>

<template>
  <div class="page">
    <PageHeader :title="id ? '编辑模板' : '新建模板'" :subtitle="id ? `模板 ID: ${id}` : '通过左侧组件搭建标注表单'" />

    <el-form :model="form" inline style="margin-bottom:12px">
      <el-form-item label="模板名称" required>
        <el-input v-model="form.name" placeholder="如：文本情感分类" style="width:260px" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" placeholder="模板用途说明" style="width:360px" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="save">保存</el-button>
        <el-button type="success" @click="saveAndPublish">保存并发布</el-button>
        <el-button @click="router.back()">返回</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="16">
      <el-col :span="5">
        <el-card shadow="never" class="panel">
          <template #header>
            <div style="display:flex;align-items:center;gap:6px"><el-icon><DocumentAdd /></el-icon>组件库</div>
          </template>
          <div class="palette">
            <div v-for="t in MATERIAL_TYPES" :key="t.value" class="palette-item" @click="addMaterial(t.value)">
              <el-icon><component :is="t.icon" /></el-icon>
              <span>{{ t.label }}</span>
              <el-icon class="plus"><Plus /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="11">
        <el-card shadow="never" class="panel">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span><el-icon style="vertical-align:middle"><Document /></el-icon> 字段画布 ({{ materials.length }})</span>
              <el-tag size="small" type="info" effect="plain">点击字段编辑属性</el-tag>
            </div>
          </template>
          <div v-if="!materials.length" class="empty">从左侧组件库添加字段</div>
          <DraggableFree>
            <div v-for="m in materials" :key="m.id" class="canvas-item" :class="{ active: selectedId === m.id }" @click="selectMaterial(m.id)">
              <div class="ci-head">
                <el-tag size="small" effect="plain">{{ m.type }}</el-tag>
                <span class="ci-label">{{ m.label }}</span>
                <span class="ci-key">{{ m.fieldKey }}</span>
                <span class="ci-actions">
                  <el-button size="small" link @click.stop="moveUp(m.id)">↑</el-button>
                  <el-button size="small" link @click.stop="moveDown(m.id)">↓</el-button>
                  <el-button size="small" link type="danger" @click.stop="removeMaterial(m.id)"><el-icon><Delete /></el-icon></el-button>
                </span>
              </div>
              <div class="ci-required">
                <el-tag v-if="m.required" size="small" type="danger" effect="plain">必填</el-tag>
              </div>
            </div>
          </DraggableFree>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never" class="panel">
          <template #header>属性配置</template>
          <div v-if="!selected" class="empty">选择左侧字段以配置属性</div>
          <el-form v-else :model="selected" label-position="top">
            <el-form-item label="字段标识 fieldKey" required>
              <el-input v-model="selected.fieldKey" />
            </el-form-item>
            <el-form-item label="显示标签 label">
              <el-input v-model="selected.label" />
            </el-form-item>
            <el-form-item label="类型">
              <el-select v-model="selected.type" style="width:100%">
                <el-option v-for="t in MATERIAL_TYPES" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="是否必填">
              <el-switch v-model="selected.required" />
            </el-form-item>
            <el-form-item v-if="['radio','checkbox','select'].includes(selected.type)" label="选项">
              <div v-for="(opt, idx) in selected.options || []" :key="idx" style="display:flex;gap:6px;margin-bottom:6px">
                <el-input v-model="selected.options![idx]" />
                <el-button size="small" type="danger" @click="removeOption(selected, idx)"><el-icon><Delete /></el-icon></el-button>
              </div>
              <el-button size="small" @click="addOption(selected)">新增选项</el-button>
            </el-form-item>
            <el-form-item v-if="selected.type === 'textarea'" label="行数">
              <el-input-number v-model="selected.props!.rows" :min="1" :max="20" />
            </el-form-item>
            <el-form-item v-if="selected.type === 'select'" label="多选">
              <el-switch v-model="selected.props!.multiple" />
            </el-form-item>
            <el-form-item v-if="selected.type === 'number'" label="最小值">
              <el-input-number v-model="selected.props!.min" controls-position="right" />
            </el-form-item>
            <el-form-item v-if="selected.type === 'number'" label="最大值">
              <el-input-number v-model="selected.props!.max" controls-position="right" />
            </el-form-item>
            <el-form-item v-if="selected.type === 'rating'" label="最大分值">
              <el-input-number v-model="selected.props!.max" :min="1" :max="10" controls-position="right" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.panel { height: calc(100vh - 250px); min-height: 420px; display:flex; flex-direction:column; }
.panel :deep(.el-card__body) { flex:1; overflow:auto; }
.palette { display:flex; flex-direction:column; gap:8px; }
.palette-item { display:flex; align-items:center; gap:8px; padding:10px 12px; border:1px solid #eef0f5; border-radius:8px; cursor:pointer; font-size:14px; color:#1f2430; transition:all .15s; }
.palette-item:hover { border-color: var(--lh-primary); color: var(--lh-primary); background:#f5f7ff; }
.palette-item .plus { margin-left:auto; color:#c0c4cc; }
.canvas-item { border:1px solid #eef0f5; border-radius:8px; padding:10px 12px; margin-bottom:10px; cursor:pointer; transition:all .15s; }
.canvas-item:hover { border-color:#b8c0f5; }
.canvas-item.active { border-color: var(--lh-primary); background:#f5f7ff; }
.ci-head { display:flex; align-items:center; gap:8px; }
.ci-label { font-weight:600; color:#1f2430; }
.ci-key { color:#8a93a6; font-size:12px; font-family: monospace; }
.ci-actions { margin-left:auto; }
.empty { text-align:center; padding:40px; color:#a0a6b5; font-size:14px; }
</style>