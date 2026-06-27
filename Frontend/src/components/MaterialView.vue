<script setup lang="ts">
import type { TemplateSchema } from '@/types'
import { MATERIAL_TYPE_LABEL } from '@/constants'
import { prettyJson } from '@/utils'

const props = defineProps<{
  schema: TemplateSchema
  result: Record<string, any> | null
  raw?: Record<string, any> | null
}>()

function val(fieldKey: string) {
  return props.result ? props.result[fieldKey] : null
}

function isArray(v: any): boolean {
  return Array.isArray(v)
}
</script>

<template>
  <div class="material-view">
    <el-descriptions v-if="schema.materials.length" :column="1" border>
      <el-descriptions-item v-for="m in schema.materials" :key="m.id" :label="m.label">
        <template v-if="m.type === 'checkbox' || isArray(val(m.fieldKey))">
          <el-tag v-for="(v, i) in (val(m.fieldKey) || [])" :key="i" size="small" effect="plain" style="margin-right:6px">{{ v }}</el-tag>
          <span v-if="!(val(m.fieldKey) || []).length" class="muted">—</span>
        </template>
        <el-tag v-else-if="m.type === 'radio' || m.type === 'select'" type="info" effect="plain">{{ val(m.fieldKey) ?? '—' }}</el-tag>
        <a v-else-if="m.type === 'image'" :href="val(m.fieldKey)" target="_blank">
          <el-image v-if="val(m.fieldKey)" :src="val(m.fieldKey)" fit="cover" style="width:120px;height:120px;border-radius:8px" />
          <span v-else class="muted">—</span>
        </a>
        <a v-else-if="m.type === 'file'" :href="val(m.fieldKey)" target="_blank">{{ val(m.fieldKey) || '—' }}</a>
        <pre v-else-if="m.type === 'json'" class="json-block">{{ prettyJson(val(m.fieldKey)) }}</pre>
        <span v-else-if="m.type === 'llm_prompt'">
          <el-tag size="small" type="warning" effect="plain">{{ MATERIAL_TYPE_LABEL[m.type] }}</el-tag>
          <div style="white-space:pre-wrap;margin-top:4px">{{ val(m.fieldKey) || '—' }}</div>
        </span>
        <span v-else>{{ val(m.fieldKey) ?? '—' }}</span>
      </el-descriptions-item>
    </el-descriptions>
    <el-empty v-else description="无字段" />
  </div>
</template>

<style scoped lang="scss">
.material-view .muted { color: #c0c4cc; }
.json-block { background:#f6f8fa; padding:10px; border-radius:6px; margin:0; font-size:12px; max-height:280px; overflow:auto; }
</style>