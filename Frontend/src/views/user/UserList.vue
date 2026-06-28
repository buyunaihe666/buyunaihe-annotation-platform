<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listUsers, createUser, updateUser, deleteUser, batchDeleteUsers } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import type { User, RoleCode } from '@/types'
import { ROLE_CODES, ROLE_LABEL } from '@/constants'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { formatDate } from '@/utils'
import { Delete, Plus } from '@element-plus/icons-vue'

const authStore = useAuthStore()
const list = ref<User[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = reactive<{
  id?: number; username: string; password: string; nickname: string
  role_code: RoleCode; email: string; phone: string
}>({ username:'', password:'', nickname:'', role_code:'labeler', email:'', phone:'' })
const selectedIds = ref<number[]>([])
const deleteMode = ref(false)

const isAdmin = computed(() => authStore.role === 'admin' || authStore.role === 'owner')
const allSelected = computed(() =>
  list.value.length > 0 && selectedIds.value.length === list.value.length
)
const someSelected = computed(() =>
  selectedIds.value.length > 0 && selectedIds.value.length < list.value.length
)

async function load() {
  loading.value = true
  try { list.value = await listUsers() } finally { loading.value = false }
}

function openCreate() {
  isEdit.value = false
  Object.assign(form, { id: undefined, username:'', password:'', nickname:'', role_code:'labeler', email:'', phone:'' })
  dialogVisible.value = true
}

function openEdit(row: User) {
  isEdit.value = true
  Object.assign(form, {
    id: row.id, username: row.username, password: '', nickname: row.nickname || '',
    role_code: row.role_code, email: row.email || '', phone: row.phone || ''
  })
  dialogVisible.value = true
}

async function submit() {
  if (!form.username) { ElMessage.warning('请填写用户名'); return }
  if (!isEdit.value && !form.password) { ElMessage.warning('请填写密码'); return }
  try {
    if (isEdit.value && form.id) {
      const payload: any = { nickname: form.nickname, role_code: form.role_code, email: form.email, phone: form.phone }
      if (form.password) payload.password = form.password
      await updateUser(form.id, payload)
      ElMessage.success('已更新')
    } else {
      await createUser({
        username: form.username, password: form.password, nickname: form.nickname,
        role_code: form.role_code, email: form.email, phone: form.phone
      })
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    load()
  } catch {}
}

async function remove(row: User) {
  await ElMessageBox.confirm(`删除用户「${row.username}」？`, '删除', { type: 'error' })
  await deleteUser(row.id)
  ElMessage.success('已删除')
  load()
}

function onSelectionChange(rows: User[]) {
  selectedIds.value = rows.map(r => r.id)
}

function toggleSelectAll(checked: boolean) {
  if (checked) {
    selectedIds.value = list.value.map(r => r.id)
  } else {
    selectedIds.value = []
  }
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要删除的用户')
    return
  }
  await ElMessageBox.confirm(
    `确定删除选中的 ${selectedIds.value.length} 个用户吗？`,
    '批量删除',
    { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
  )
  await batchDeleteUsers(selectedIds.value)
  ElMessage.success(`已删除 ${selectedIds.value.length} 个用户`)
  selectedIds.value = []
  deleteMode.value = false
  load()
}

function toggleDeleteMode() {
  deleteMode.value = !deleteMode.value
  if (!deleteMode.value) {
    selectedIds.value = []
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <PageHeader title="用户管理" subtitle="管理平台用户与角色权限" />
    <el-card shadow="never">
      <div class="toolbar">
        <div class="toolbar-left"></div>
        <div class="toolbar-right">
          <template v-if="isAdmin && deleteMode">
            <el-checkbox
              :model-value="allSelected"
              :indeterminate="someSelected"
              @change="toggleSelectAll"
            >
              {{ allSelected ? '取消全选' : '全选' }}
            </el-checkbox>
            <el-button
              v-if="selectedIds.length > 0"
              type="danger"
              :icon="Delete"
              @click="handleBatchDelete"
              style="margin-left: 12px"
            >
              删除选中 ({{ selectedIds.length }})
            </el-button>
            <el-button @click="toggleDeleteMode" style="margin-left: 8px">取消</el-button>
          </template>
          <template v-else>
            <el-button
              v-if="isAdmin && list.length > 0"
              :icon="Delete"
              @click="toggleDeleteMode"
            >
              删除
            </el-button>
            <el-button type="primary" :icon="Plus" @click="openCreate" style="margin-left: 8px">新增用户</el-button>
          </template>
        </div>
      </div>
      <el-table :data="list" v-loading="loading" border stripe @selection-change="onSelectionChange" row-key="id">
        <el-table-column v-if="isAdmin && deleteMode" type="selection" width="50" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="nickname" label="昵称" width="140" />
        <el-table-column label="角色" width="140"><template #default="{ row }"><el-tag size="small" effect="plain">{{ ROLE_LABEL[row.role_code as RoleCode] }}</el-tag></template></el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column prop="phone" label="电话" width="140" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column label="创建时间" width="170"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="isAdmin" size="small" link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><EmptyState icon="User" description="暂无用户" /></template>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="480px">
      <el-form :model="form" label-position="top">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" :disabled="isEdit" />
        </el-form-item>
        <el-form-item :label="isEdit ? '密码（留空不修改）' : '密码'" :required="!isEdit">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="昵称"><el-input v-model="form.nickname" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_code" style="width:100%">
            <el-option v-for="r in ROLE_CODES" :key="r.code" :label="r.label" :value="r.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="电话"><el-input v-model="form.phone" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.toolbar-left {
  display: flex;
  align-items: center;
}
.toolbar-right {
  display: flex;
  align-items: center;
}

:deep(.el-table__body tr.is-selected > td) {
  background-color: #f5f3ff !important;
}

:deep(.el-table__body tr:hover > td) {
  background-color: #f8fafc !important;
}
</style>
