<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSquare, claimItem, deleteTask, batchDeleteTasks } from '@/api'
import { useAuthStore } from '@/stores/auth'
import type { Task } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import EmptyState from '@/components/EmptyState.vue'
import { formatDate } from '@/utils'
import { Delete } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()
const list = ref<Task[]>([])
const loading = ref(false)
const keyword = ref('')
const claiming = ref<number | null>(null)
const selectedIds = ref<number[]>([])
const deleteMode = ref(false)
const activeTab = ref('available')
const claimCount = ref(5) // 默认领取5个
const claimCountMap = ref<Record<number, number>>({}) // 每个任务的领取数量

const isAdmin = computed(() => authStore.role === 'admin' || authStore.role === 'owner')
const filteredList = computed(() => {
  if (!keyword.value.trim()) return list.value
  const kw = keyword.value.trim().toLowerCase()
  return list.value.filter(t =>
    t.name.toLowerCase().includes(kw) ||
    (t.description || '').toLowerCase().includes(kw) ||
    String(t.id).includes(kw)
  )
})
const allSelected = computed(() =>
  filteredList.value.length > 0 && selectedIds.value.length === filteredList.value.length
)
const someSelected = computed(() =>
  selectedIds.value.length > 0 && selectedIds.value.length < filteredList.value.length
)

async function load() {
  loading.value = true
  try {
    list.value = await getSquare({ keyword: keyword.value || undefined, tab: activeTab.value })
  } finally {
    loading.value = false
  }
}

function handleTabChange() {
  keyword.value = ''
  selectedIds.value = []
  deleteMode.value = false
  load()
}

async function claim(task: Task) {
  const count = claimCountMap.value[task.id] ?? claimCount
  if (task.available_count !== undefined && task.available_count === 0) {
    ElMessage.warning('该任务已无可领取的标注项')
    return
  }
  claiming.value = task.id
  try {
    const res = await claimItem(task.id, count)
    ElMessage.success(`已领取 ${res.claimed_count} 个标注项`)
    // 切换到已领取 tab
    activeTab.value = 'mine_active'
    await load()
  } catch (e: any) {
    if (e?.response?.data?.message) {
      ElMessage.error(e.response.data.message)
    }
  } finally {
    claiming.value = null
  }
}

function enterTask(task: Task) {
  if (activeTab.value === 'available') {
    claim(task)
  } else if (task.my_items && task.my_items.length > 0) {
    // 找第一个非完成状态的标注项
    const active = task.my_items.find(i => i.status === 'annotating' || i.status === 'submitted' || i.status === 'reviewed')
    router.push(`/workbench/${(active || task.my_items[0]).id}`)
  }
}

function gotoItem(itemId: number) {
  router.push(`/workbench/${itemId}`)
}

function toggleSelect(task: Task) {
  const idx = selectedIds.value.indexOf(task.id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(task.id)
}

function toggleSelectAll(checked: boolean) {
  if (checked) {
    selectedIds.value = filteredList.value.map(t => t.id)
  } else {
    selectedIds.value = []
  }
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要删除的任务')
    return
  }
  await ElMessageBox.confirm(
    `确定删除选中的 ${selectedIds.value.length} 个任务？`,
    '批量删除',
    { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
  )
  await batchDeleteTasks(selectedIds.value)
  ElMessage.success(`已删除 ${selectedIds.value.length} 个任务`)
  selectedIds.value = []
  deleteMode.value = false
  await load()
}

function toggleDeleteMode() {
  deleteMode.value = !deleteMode.value
  if (!deleteMode.value) {
    selectedIds.value = []
  }
}

const emptyText = computed(() => {
  if (activeTab.value === 'available') return '暂无可领取任务'
  if (activeTab.value === 'mine_active') return '暂无进行中的任务'
  return '暂无已完成的任务'
})

// 计算总金额
const grandTotalReward = computed(() => {
  return list.value.reduce((sum, t) => sum + (t.total_reward || 0), 0)
})

// 已发布tab: 所有未被领取任务的总金额
const availableTotalReward = computed(() => {
  return list.value.reduce((sum, t) => {
    const perItem = t.reward_rules?.per_item || 0
    return sum + (t.available_count || 0) * perItem
  }, 0)
})

// 已领取tab: 我已领取的所有标注项总金额
const mineActiveTotalReward = computed(() => {
  return list.value.reduce((sum, t) => {
    const perItem = t.reward_rules?.per_item || 0
    const count = t.my_items?.length || 0
    return sum + count * perItem
  }, 0)
})

// 当前活跃Tab对应的总金额
const currentTotalReward = computed(() => {
  if (activeTab.value === 'available') return availableTotalReward.value
  if (activeTab.value === 'mine_active') return mineActiveTotalReward.value
  return grandTotalReward.value
})

// 统计已领取/已完成的标注项数
function itemCount(t: Task) {
  return t.my_items?.length || 0
}

onMounted(load)
</script>

<template>
  <div class="page">
    <PageHeader title="标注广场" subtitle="领取已发布任务进入标注工作台" />
    <el-card shadow="never">
      <div class="tabs-header">
        <el-tabs v-model="activeTab" @tab-change="handleTabChange" class="square-tabs">
          <el-tab-pane label="已发布" name="available" />
          <el-tab-pane label="已领取" name="mine_active" />
          <el-tab-pane label="已完成" name="mine_done" />
        </el-tabs>
        <!-- Tab栏右侧总金额 -->
        <div class="tab-reward-area">
          <span class="tab-reward-label">总金额：</span>
          <span class="tab-reward-amount">¥{{ currentTotalReward.toFixed(2) }}</span>
        </div>
      </div>

      <div class="toolbar">
        <div class="toolbar-left">
          <el-input v-model="keyword" placeholder="搜索任务名称" clearable style="width:280px" @keyup.enter="load">
            <template #append><el-button @click="load">搜索</el-button></template>
          </el-input>
        </div>
        <div class="toolbar-right" v-if="isAdmin && activeTab === 'available'">
          <template v-if="deleteMode">
            <el-checkbox :model-value="allSelected" :indeterminate="someSelected" @change="toggleSelectAll">
              {{ allSelected ? '取消全选' : '全选' }}
            </el-checkbox>
            <el-button v-if="selectedIds.length > 0" type="danger" :icon="Delete" @click="handleBatchDelete" style="margin-left:12px">
              删除选中 ({{ selectedIds.length }})
            </el-button>
            <el-button @click="toggleDeleteMode" style="margin-left:8px">取消</el-button>
          </template>
          <template v-else>
            <el-button v-if="list.length > 0" :icon="Delete" @click="toggleDeleteMode">删除</el-button>
          </template>
        </div>
      </div>

      <div class="content-area">
        <el-empty v-if="!filteredList.length && !loading" :description="emptyText">
          <el-button @click="load">刷新</el-button>
        </el-empty>
        <el-row :gutter="16" v-else>
          <el-col v-for="t in filteredList" :key="t.id" :span="8" style="margin-bottom:16px">
            <el-card shadow="hover" class="task-card" :class="{ 'is-selected': selectedIds.includes(t.id) }">
              <div class="tc-head">
                <div class="tc-head-left">
                  <div class="checkbox-col" v-if="isAdmin && deleteMode && activeTab === 'available'">
                    <el-checkbox :model-value="selectedIds.includes(t.id)" @change="() => toggleSelect(t)" />
                  </div>
                  <span class="tc-name">{{ t.name }}</span>
                </div>
                <div class="tc-head-right">
                <!-- 已发布: 总可领取金额 -->
                <span class="reward-badge" v-if="activeTab === 'available' && t.reward_rules?.per_item && t.available_count !== undefined">
                  ¥{{ (t.available_count * t.reward_rules.per_item).toFixed(2) }}
                </span>
                <!-- 已领取: 当前任务领取总金额 -->
                <span class="reward-badge" v-if="activeTab === 'mine_active' && t.reward_rules?.per_item && t.my_items">
                  ¥{{ (t.my_items.length * t.reward_rules.per_item).toFixed(2) }}
                </span>
                <!-- 已完成: 当前任务总奖励 -->
                <span class="reward-badge" v-if="activeTab === 'mine_done' && t.total_reward">¥{{ t.total_reward.toFixed(2) }}</span>
                <StatusTag :status="t.status" v-if="activeTab === 'available'" />
                <StatusTag status="annotating" v-else-if="activeTab === 'mine_active'" />
                <StatusTag status="approved" v-else-if="activeTab === 'mine_done'" />
              </div>
              </div>

              <div class="tc-desc">{{ t.description || '无描述' }}</div>
              <div class="tc-meta">
                <span>{{ t.template?.name || '关联模板' }}</span>
                <span>·</span>
                <span>{{ t.dataset?.name || '数据集' }}</span>
                <span v-if="t.enable_ai_suggestion">· AI 建议</span>
                <span v-if="t.enable_ai_audit">· AI 审核</span>
              </div>
              <div class="tc-meta sm">{{ formatDate(t.created_at) }}</div>

              <!-- 已发布: 显示可领取数量 + 单价 -->
        <div class="tc-meta-row" v-if="activeTab === 'available' && t.available_count !== undefined">
          <span class="reward-text">
            可领取: {{ t.available_count }} / {{ t.total_count }}
          </span>
          <span class="unit-price" v-if="t.reward_rules?.per_item">单价: ¥{{ t.reward_rules.per_item }}</span>
        </div>

              <!-- 已领取: 显示标注项数 + 单价 -->
        <div class="tc-meta-row" v-if="activeTab === 'mine_active' && t.my_items">
          <span class="reward-text">标注项: {{ t.my_items.length }} 个
            <span class="review-pending" v-if="t.my_items.some(i => i.status === 'submitted' || i.status === 'reviewed')">
              ({{ t.my_items.filter(i => i.status === 'submitted' || i.status === 'reviewed').length }} 待审核)
            </span>
          </span>
          <span class="unit-price" v-if="t.reward_rules?.per_item">单价: ¥{{ t.reward_rules.per_item }}</span>
        </div>

        <!-- 已完成: 显示通过项数 -->
        <div class="tc-meta-row" v-if="activeTab === 'mine_done'">
          <span class="reward-text">已完成: {{ t.my_items?.filter(i => i.status === 'approved').length || 0 }} 项通过</span>
          <span class="unit-price" v-if="t.reward_rules?.per_item">单价: ¥{{ t.reward_rules.per_item }}</span>
        </div>

              <!-- 已发布: 批量领取选择器 + 按钮 -->
              <div class="claim-area" v-if="activeTab === 'available'">
                <el-input-number
                  :model-value="claimCountMap[t.id] ?? claimCount"
                  :min="1"
                  :max="Math.min(t.available_count || 1, 50)"
                  size="small"
                  style="width: 110px"
                  @change="(val: number) => claimCountMap[t.id] = val"
                />
                <el-button
                  type="primary"
                  :loading="claiming === t.id"
                  :disabled="t.available_count !== undefined && t.available_count === 0"
                  @click="claim(t)"
                >
                  {{ t.available_count === 0 ? '已领完' : '领取' }}
                </el-button>
              </div>

              <!-- 已领取/已完成: 进入按钮 -->
              <el-button
                type="primary"
                v-if="activeTab !== 'available'"
                @click="enterTask(t)"
              >
                {{ activeTab === 'mine_active' ? '继续标注' : '查看详情' }}
              </el-button>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.tabs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e4e7ed;
  padding-right: 8px;
}
.square-tabs { 
  margin-bottom: 0; 
  border-bottom: none;
  flex: 1;
}
.tab-reward-area {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 40px;
}
.tab-reward-label {
  font-size: 14px;
  color: #909399;
}
.tab-reward-amount {
  font-size: 18px;
  font-weight: 600;
  /* 黑金渐变效果 */
  background: linear-gradient(135deg, #FFE55C 0%, #D4AF37 50%, #121212 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.15);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 16px 0;
}
.toolbar-left, .toolbar-right { display: flex; align-items: center; }

.task-card {
  border-radius: 10px;
  transition: all 0.2s ease;
}
.task-card.is-selected {
  background: #f5f3ff;
  border-color: #c4b5fd;
}
.tc-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.tc-head-left { display: flex; align-items: center; gap: 8px; }
.tc-head-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.checkbox-col { flex-shrink: 0; }
.tc-name {
  font-weight: 600;
  color: #1f2430;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.reward-badge {
  font-weight: 600;
  font-size: 16px;
  /* 青金渐变效果 */
  background: linear-gradient(135deg, #56CCF2 0%, #2F80ED 50%, #F2C94C 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.price-badge {
  background: #fdf6ec;
  color: #e6a23c;
  border-radius: 10px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 600;
}
.tc-desc {
  color: #8a93a6;
  font-size: 13px;
  min-height: 38px;
}
.tc-meta {
  color: #a0a6b5;
  font-size: 12px;
  margin-top: 8px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.tc-meta.sm { margin-top: 2px; }
.reward-text {
  font-weight: 600;
  /* 青金渐变效果 */
  background: linear-gradient(135deg, #56CCF2 0%, #2F80ED 50%, #F2C94C 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.tc-meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
  font-size: 12px;
  color: #a0a6b5;
}
.unit-price {
  font-weight: 600;
  font-size: 12px;
  /* 青金渐变效果 */
  background: linear-gradient(135deg, #56CCF2 0%, #2F80ED 50%, #F2C94C 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.review-pending { color: #409eff; }

.reward-box {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.reward-label { font-size: 12px; color: #909399; }
.reward-amount {
  font-size: 18px;
  font-weight: 700;
  color: #f56c6c;
}
.reward-detail { font-size: 11px; color: #c0c4cc; }

.my-items-list {
  margin-top: 10px;
  border-top: 1px dashed #e4e7ed;
  padding-top: 8px;
}
.my-item-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}
.my-item-row:hover { background: #f5f7fa; }
.my-item-index {
  color: #909399;
  font-size: 12px;
  font-weight: 600;
  min-width: 32px;
}
.my-item-reward {
  color: #f56c6c;
  font-size: 12px;
  font-weight: 600;
}
.my-item-go {
  margin-left: auto;
  color: #c0c4cc;
  font-size: 12px;
}
.my-item-more {
  text-align: center;
  color: #c0c4cc;
  font-size: 12px;
  padding: 4px;
}

.claim-area {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.claim-area .el-button {
  flex: 1;
  margin-top: 0;
}
.el-button {
  margin-top: 12px;
  width: 100%;
}
</style>
