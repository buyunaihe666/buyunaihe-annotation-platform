<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listDatasets, createDataset, deleteDataset } from '@/api'
import type { Dataset } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import EmptyState from '@/components/EmptyState.vue'
import { formatDate } from '@/utils'

const router = useRouter()
const list = ref<Dataset[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const form = reactive({ name: '', description: '' })

async function load() {
  loading.value = true
  try { list.value = await listDatasets() } finally { loading.value = false }
}

async function submit() {
  if (!form.name) { ElMessage.warning('请填写名称'); return }
  await createDataset({ name: form.name, description: form.description })
  ElMessage.success('已创建')
  dialogVisible.value = false
  form.name = ''; form.description = ''
  load()
}

async function remove(row: Dataset) {
  await ElMessageBox.confirm(`删除数据集「${row.name}」？关联数据亦将删除。`, '删除', { type: 'error' })
  await deleteDataset(row.id)
  ElMessage.success('已删除')
  load()
}

function detail(row: Dataset) { router.push(`/datasets/${row.id}`) }

onMounted(load)
</script>

<template>
  <div class="page">
    <PageHeader title="数据集" subtitle="上传原始数据并管理字段映射" />
    <el-card shadow="never">
      <div style="display:flex;justify-content:space-between;margin-bottom:12px">
        <el-input placeholder="搜索数据集" style="width:260px" clearable @keyup.enter="load" />
        <el-button type="primary" @click="dialogVisible = true">新建数据集</el-button>
      </div>
      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="format" label="格式" width="100" />
        <el-table-column prop="file_count" label="文件数" width="90" />
        <el-table-column prop="item_count" label="样本数" width="90" />
        <el-table-column label="创建时间" width="170"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="detail(row)">详情</el-button>
            <el-button size="small" link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><EmptyState icon="Files" description="暂无数据集" /></template>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新建数据集" width="480px">
      <el-form :model="form" label-position="top">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>