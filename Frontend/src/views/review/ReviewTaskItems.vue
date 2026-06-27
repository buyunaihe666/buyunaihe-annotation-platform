<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listReviewItems } from '@/api'
import type { TaskItem } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import EmptyState from '@/components/EmptyState.vue'
import { usePagination } from '@/composables/usePagination'
import { formatDate } from '@/utils'

const route = useRoute()
const router = useRouter()
const taskId = computed(() => Number(route.params.taskId))

const items = ref<TaskItem[]>([])
const loading = ref(false)
const { page, size, total, setPage, setSize, setTotal } = usePagination(20)
const statusFilter = ref('submitted')

const STATUS_OPTIONS = [
  { label: '已提交', value: 'submitted' },
  { label: 'AI 审核中', value: 'ai_reviewing' },
  { label: '已审核', value: 'reviewed' },
  { label: '已通过', value: 'approved' },
  { label: '已驳回', value: 'rejected' }
]

async function load() {
  loading.value = true
  try {
    const res = await listReviewItems(taskId.value, {
      status: statusFilter.value || undefined,
      page: page.value,
      size: size.value
    })
    items.value = res.items || []
    setTotal(res.total || 0)
  } finally {
    loading.value = false
  }
}

function onPage(p: number) { setPage(p); load() }
function onSize(s: number) { setSize(s); load() }
function work(row: TaskItem) { router.push(`/review/workbench/${row.id}`) }

onMounted(load)
</script>

<template>
  <div class="page">
    <PageHeader title="待审核项" subtitle="选择一项进入审核工作台" />
    <el-button @click="router.push('/review')">返回任务列表</el-button>
    <el-card shadow="never" style="margin-top:12px">
      <div style="display:flex;justify-content:space-between;margin-bottom:12px">
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width:160px" @change="() => { setPage(1); load() }">
          <el-option v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-button @click="load">刷新</el-button>
      </div>
      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="index" label="序号" width="80" />
        <el-table-column label="状态" width="120"><template #default="{ row }"><StatusTag :status="row.status" /></template></el-table-column>
        <el-table-column label="更新时间" width="170"><template #default="{ row }">{{ formatDate(row.updated_at) }}</template></el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }"><el-button size="small" type="primary" link @click="work(row)">审核</el-button></template>
        </el-table-column>
        <template #empty><EmptyState icon="Connection" description="暂无待审核项" /></template>
      </el-table>
      <el-pagination
        style="margin-top:12px;justify-content:flex-end;display:flex"
        :current-page="page" :page-size="size" :total="total"
        layout="total, prev, pager, next, sizes"
        @current-change="onPage" @size-change="onSize"
      />
    </el-card>
  </div>
</template>