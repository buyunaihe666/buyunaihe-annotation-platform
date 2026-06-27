<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getDataset, getDatasetItems, uploadDatasetFile, mapFields, listTemplates } from '@/api'
import type { Dataset, DatasetItem, Template } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { usePagination } from '@/composables/usePagination'
import { formatDate, prettyJson } from '@/utils'

const route = useRoute()
const router = useRouter()
const id = computed(() => Number(route.params.id))

const dataset = ref<Dataset | null>(null)
const items = ref<DatasetItem[]>([])
const fields = ref<string[]>([])
const loadingItems = ref(false)
const { page, size, total, setPage, setSize, setTotal } = usePagination(20)

const uploadRef = ref()
const uploadLoading = ref(false)

const templates = ref<Template[]>([])
const selectedTemplateId = ref<number | undefined>()

const templateFields = computed(() => {
  const t = templates.value.find(x => x.id === selectedTemplateId.value)
  if (!t) return []
  return (t.schema?.materials || []).map(m => m.fieldKey)
})

const mapping = reactive<Record<string, string>>({})

async function loadDataset() {
  dataset.value = await getDataset(id.value)
  if (dataset.value?.field_mapping) {
    Object.assign(mapping, dataset.value.field_mapping)
  }
}

async function loadItems() {
  loadingItems.value = true
  try {
    const res = await getDatasetItems(id.value, { page: page.value, size: size.value })
    items.value = res.items || []
    setTotal(res.total || 0)
    if (res.fields?.length) fields.value = res.fields
    else if (items.value.length) fields.value = Object.keys(items.value[0].raw_data || {})
  } finally {
    loadingItems.value = false
  }
}

async function onUpload(opts: any) {
  uploadLoading.value = true
  try {
    await uploadDatasetFile(id.value, opts.file)
    ElMessage.success('上传并解析完成')
    await loadDataset()
    await loadItems()
  } catch (e) {
    uploadRef.value?.clearFiles()
  } finally {
    uploadLoading.value = false
  }
}

async function saveMapping() {
  await mapFields(id.value, mapping)
  ElMessage.success('字段映射已保存')
  loadDataset()
}

function onPage(p: number) { setPage(p); loadItems() }
function onSize(s: number) { setSize(s); loadItems() }

onMounted(async () => {
  await loadDataset()
  await loadItems()
  templates.value = await listTemplates({ status: 'published' })
})
</script>

<template>
  <div class="page">
    <PageHeader :title="`数据集 · ${dataset?.name || ''}`" :subtitle="dataset?.description" />
    <el-button @click="router.back()">返回</el-button>

    <el-row :gutter="16" style="margin-top:12px">
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>上传数据文件</template>
          <el-upload
            ref="uploadRef"
            drag
            :auto-upload="true"
            :show-file-list="false"
            :http-request="onUpload"
            accept=".json,.jsonl,.csv,.xlsx"
            v-loading="uploadLoading"
          >
            <el-icon class="el-icon--upload"><Upload /></el-icon>
            <div class="el-upload__text">拖拽文件至此，或<em>点击上传</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 .json / .jsonl / .csv / .xlsx 格式</div>
            </template>
          </el-upload>
          <div style="margin-top:10px;color:#8a93a6;font-size:13px">
            样本数：{{ dataset?.item_count || 0 }} · 文件数：{{ dataset?.file_count || 0 }} · 格式：{{ dataset?.format || '-' }}
          </div>
        </el-card>
      </el-col>

      <el-col :span="24">
        <el-card shadow="never" style="margin-top:16px">
          <template #header>样本预览</template>
          <el-table :data="items" v-loading="loadingItems" border stripe max-height="420">
            <el-table-column prop="index" label="#" width="60" />
            <el-table-column v-for="f in fields.slice(0, 6)" :key="f" :label="f" min-width="160" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="typeof row.raw_data?.[f] === 'object'">{{ prettyJson(row.raw_data?.[f]) }}</span>
                <span v-else>{{ row.raw_data?.[f] ?? '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="完整数据" width="120">
              <template #default="{ row }">
                <el-popover placement="left" :width="420" trigger="hover">
                  <template #reference><el-button size="small" link>查看</el-button></template>
                  <pre style="max-height:280px;overflow:auto;font-size:11px">{{ prettyJson(row.raw_data) }}</pre>
                </el-popover>
              </template>
            </el-table-column>
            <template #empty><EmptyState icon="Files" description="暂无样本，请上传文件" /></template>
          </el-table>
          <el-pagination
            style="margin-top:12px;justify-content:flex-end;display:flex"
            :current-page="page" :page-size="size" :total="total"
            layout="total, prev, pager, next, sizes"
            @current-change="onPage" @size-change="onSize"
          />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="margin-top:16px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>字段映射（模板字段 → 数据集字段）</span>
          <el-button type="primary" size="small" @click="saveMapping">保存映射</el-button>
        </div>
      </template>
      <div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:12px">
        <el-select v-model="selectedTemplateId" placeholder="选择已发布模板" style="width:280px">
          <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
      </div>
      <EmptyState v-if="!selectedTemplateId" description="请先选择模板以配置字段映射" />
      <el-table v-else :data="templateFields.map(f => ({ fieldKey: f }))" border>
        <el-table-column prop="fieldKey" label="模板字段标识" width="220" />
        <el-table-column label="数据集字段">
          <template #default="{ row }">
            <el-select v-model="mapping[row.fieldKey]" clearable placeholder="选择数据集字段" style="width:280px">
              <el-option v-for="f in fields" :key="f" :label="f" :value="f" />
            </el-select>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>