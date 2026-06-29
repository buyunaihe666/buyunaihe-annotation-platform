<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { Tools, User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const form = reactive({ username: 'admin', password: 'admin' })
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
        <div class="brand-icon">
          <el-icon :size="40" color="#6366f1"><Tools /></el-icon>
        </div>
        <h1>不予奈何</h1>
        <p>AI 数据标注平台</p>
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
      <div class="hint">
        默认账号：admin / admin123
        <br/>
        <span class="hint-sub">标注员: labeler1 / admin123 | 审核员: reviewer1 / admin123</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-page {
  min-height:100%;
  display:flex;
  align-items:center;
  justify-content:center;
  background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
  position: relative;
  overflow: hidden;
  &::before {
    content: '';
    position: absolute;
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, transparent 70%);
    border-radius: 50%;
    top: -200px;
    right: -200px;
  }
  &::after {
    content: '';
    position: absolute;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.06) 0%, transparent 70%);
    border-radius: 50%;
    bottom: -150px;
    left: -150px;
  }
}
.login-card {
  width: 420px;
  background: #fff;
  border-radius: 20px;
  padding: 40px;
  box-shadow: 0 25px 50px -12px rgba(99, 102, 241, 0.15);
  position: relative;
  z-index: 1;
  border: 1px solid var(--lh-border);
}
.login-brand {
  text-align:center;
  margin-bottom: 32px;
}
.brand-icon {
  width: 80px;
  height: 80px;
  border-radius: 20px;
  background: var(--lh-primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}
.login-brand h1 {
  margin: 0;
  font-size: 30px;
  color: var(--lh-text);
  letter-spacing: -0.8px;
  font-weight: 700;
}
.login-brand p {
  margin: 8px 0 0;
  color: var(--lh-text-soft);
  font-size: 14px;
}
.submit {
  width:100%;
  height:46px;
  font-size:16px;
  font-weight: 600;
  margin-top: 8px;
}
.hint {
  text-align:center;
  color: var(--lh-text-soft);
  font-size: 13px;
  margin-top: 20px;
  line-height: 1.8;
}
.hint-sub {
  font-size: 12px;
  color: #cbd5e1;
}
</style>
