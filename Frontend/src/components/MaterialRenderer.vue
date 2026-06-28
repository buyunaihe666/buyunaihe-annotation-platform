<script setup lang="ts">
import { ref, watch, computed, reactive } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import type { TemplateSchema } from '@/types'
import { MATERIAL_TYPE_LABEL } from '@/constants'

const props = defineProps<{
  schema: TemplateSchema
  modelValue: Record<string, any>
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: Record<string, any>): void
}>()

const formRef = ref<FormInstance>()
const local = ref<Record<string, any>>({ ...(props.modelValue || {}) })
const jsonText = reactive<Record<string, string>>({})

watch(
  () => props.modelValue,
  (v) => {
    const merged: Record<string, any> = {}
    for (const m of props.schema.materials) {
      merged[m.fieldKey] = (v && v[m.fieldKey] !== undefined) ? v[m.fieldKey] : (local.value[m.fieldKey] ?? defaultFor(m))
    }
    local.value = merged
    for (const m of props.schema.materials) {
      if (m.type === 'json' && typeof local.value[m.fieldKey] === 'object' && local.value[m.fieldKey] !== null) {
        jsonText[m.fieldKey] = JSON.stringify(local.value[m.fieldKey], null, 2)
      }
    }
  },
  { immediate: true, deep: true }
)

function defaultFor(m: any): any {
  if (m.type === 'checkbox') return []
  if (m.type === 'select' && m.props?.multiple) return []
  if (m.type === 'number') return undefined
  return undefined
}

const rules = computed<FormRules>(() => {
  const r: FormRules = {}
  for (const m of props.schema.materials) {
    const field: any[] = []
    if (m.required) {
      field.push({
        required: true,
        message: `请填写「${m.label}」`,
        trigger: ['blur', 'change']
      })
    }
    if (m.type === 'number') {
      field.push({
        validator: (_: any, val: any, cb: (err?: Error) => void) => {
          if (val === '' || val === undefined || val === null) return cb()
          if (Number.isNaN(Number(val))) return cb(new Error('请输入数字'))
          cb()
        },
        trigger: 'blur'
      })
    }
    r[m.fieldKey] = field
  }
  return r
})

function sync() {
  emit('update:modelValue', { ...local.value })
}

function onInput() {
  sync()
}

function onJsonInput(m: any) {
  const text = jsonText[m.fieldKey] || ''
  try {
    local.value[m.fieldKey] = text ? JSON.parse(text) : undefined
    sync()
  } catch {
    // keep raw text, do not sync parsed value
  }
}

function onUploadSuccess(m: any, r: any) {
  local.value[m.fieldKey] = r?.data?.url || (typeof r === 'string' ? r : '')
  sync()
}

async function validate(): Promise<boolean> {
  if (!formRef.value) return false
  try {
    await formRef.value.validate()
    sync()
    return true
  } catch {
    ElMessage.warning('请检查表单必填项')
    return false
  }
}

function reset() {
  formRef.value?.resetFields()
  local.value = {}
  sync()
}

defineExpose({ validate, reset, sync })
</script>

<template>
  <el-form ref="formRef" :model="local" :rules="rules" label-position="top" class="material-form">
    <el-form-item
      v-for="m in schema.materials"
      :key="m.id"
      :label="m.label + (m.required ? ' *' : '')"
      :prop="m.fieldKey"
    >
      <el-input v-if="m.type === 'text'" v-model="local[m.fieldKey]" :placeholder="`请输入${m.label}`" @input="onInput" />
      <el-input v-else-if="m.type === 'textarea'" v-model="local[m.fieldKey]" type="textarea" :rows="m.props?.rows || 4" :placeholder="`请输入${m.label}`" @input="onInput" />
      <el-input-number v-else-if="m.type === 'number'" v-model="local[m.fieldKey]" :min="m.props?.min" :max="m.props?.max" :step="m.props?.step || 1" controls-position="right" @change="onInput" />
      <el-radio-group v-else-if="m.type === 'radio'" v-model="local[m.fieldKey]" @change="onInput">
        <el-radio v-for="opt in m.options || []" :key="opt" :value="opt">{{ opt }}</el-radio>
      </el-radio-group>
      <el-checkbox-group v-else-if="m.type === 'checkbox'" v-model="local[m.fieldKey]" @change="onInput">
        <el-checkbox v-for="opt in m.options || []" :key="opt" :value="opt">{{ opt }}</el-checkbox>
      </el-checkbox-group>
      <el-select v-else-if="m.type === 'select'" v-model="local[m.fieldKey]" clearable :multiple="m.props?.multiple" :placeholder="`请选择${m.label}`" @change="onInput">
        <el-option v-for="opt in m.options || []" :key="opt" :label="opt" :value="opt" />
      </el-select>
      <el-upload v-else-if="m.type === 'file'" :auto-upload="true" action="/api/upload" :on-success="(r:any)=>onUploadSuccess(m, r)">
        <el-button type="primary" plain>选择文件</el-button>
      </el-upload>
      <el-upload v-else-if="m.type === 'image'" :show-file-list="false" action="/api/upload" :on-success="(r:any)=>onUploadSuccess(m, r)">
        <el-image v-if="local[m.fieldKey]" :src="local[m.fieldKey]" fit="cover" style="width:140px;height:140px;border-radius:8px" />
        <div v-else class="img-placeholder">点击上传图片</div>
      </el-upload>
      <el-input v-else-if="m.type === 'json'" v-model="jsonText[m.fieldKey]" type="textarea" :rows="6" placeholder="请输入合法 JSON" @input="onJsonInput(m)" />
      <div v-else-if="m.type === 'llm_prompt'" class="llm-prompt-box">
        <el-alert :title="`LLM 提示字段 · ${MATERIAL_TYPE_LABEL[m.type]}`" type="info" :closable="false" show-icon />
        <el-input v-model="local[m.fieldKey]" type="textarea" :rows="4" :placeholder="`请输入${m.label}`" @input="onInput" />
      </div>
    </el-form-item>
  </el-form>
</template>

<style scoped lang="scss">
.material-form :deep(.el-form-item__label) { font-weight: 500; color: #1f2430; }
.img-placeholder { width: 140px; height: 140px; border: 1px dashed #c0c4cc; border-radius: 8px; display:flex; align-items:center; justify-content:center; color: #909399; font-size:13px; }
.llm-prompt-box .el-alert { margin-bottom: 8px; }
</style>