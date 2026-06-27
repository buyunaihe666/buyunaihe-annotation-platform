<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTemplate } from '@/api'
import type { Template, TemplateSchema } from '@/types'
import MaterialRenderer from '@/components/MaterialRenderer.vue'
import PageHeader from '@/components/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const template = ref<Template | null>(null)
const schema = ref<TemplateSchema>({ materials: [] })
const result = ref<Record<string, any>>({})
const rendererRef = ref<InstanceType<typeof MaterialRenderer>>()

async function load() {
  const id = Number(route.params.id)
  template.value = await getTemplate(id)
  schema.value = template.value?.schema || { materials: [] }
}
onMounted(load)
</script>

<template>
  <div class="page">
    <PageHeader :title="`模板预览 · ${template?.name || ''}`" subtitle="以标注员视角体验表单" />
    <el-button @click="router.back()">返回</el-button>
    <el-card shadow="never" style="margin-top:12px" v-if="schema.materials.length">
      <MaterialRenderer ref="rendererRef" :schema="schema" v-model="result" />
    </el-card>
    <el-empty v-else description="模板暂无字段" />
  </div>
</template>