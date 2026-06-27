<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { Tools } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const form = reactive({ username: 'admin', password: '123456' })
const loading = ref(false)

async function handleLogin() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.replace(redirect)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <el-icon :size="36" color="#4a6cf7"><Tools /></el-icon>
        <h1>Buyunaihe</h1>
        <p>不奈何 · AI 数据标注平台</p>
      </div>
      <el-form :model="form" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="账号">
          <el-input v-model="form.username" placeholder="请输入用户名" clearable>
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password @keyup.enter="handleLogin">
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button type="primary" :loading="loading" class="submit" @click="handleLogin">登 录</el-button>
      </el-form>
      <div class="hint">默认账号：admin / 123456</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-page {
  min-height:100%;
  display:flex; align-items:center; justify-content:center;
  background: linear-gradient(135deg, #4a6cf7 0%, #7b5cff 50%, #b06cff 100%);
}
.login-card {
  width: 400px; background: #fff; border-radius: 16px; padding: 36px 32px 28px;
  box-shadow: 0 20px 50px rgba(0,0,0,0.18);
}
.login-brand { text-align:center; margin-bottom: 24px; }
.login-brand h1 { margin: 10px 0 4px; font-size: 26px; color:#1f2430; }
.login-brand p { margin:0; color:#8a93a6; font-size:13px; }
.submit { width:100%; height:42px; font-size:15px; }
.hint { text-align:center; color:#a0a6b5; font-size:12px; margin-top:14px; }
</style>