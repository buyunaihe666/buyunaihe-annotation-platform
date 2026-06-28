<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute, RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ROLE_LABEL } from '@/constants'
import {
  DataBoard, Document, Files, List, Notebook, Download, User,
  DataAnalysis, Connection, Tools
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

interface MenuItem { index: string; title: string; icon: any; roles: string[] }

const menus = computed<MenuItem[]>(() => {
  const all: MenuItem[] = [
    { index: '/dashboard', title: '数据看板', icon: DataBoard, roles: ['owner', 'admin', 'labeler', 'reviewer'] },
    { index: '/templates', title: '标注模板', icon: Document, roles: ['owner', 'admin'] },
    { index: '/datasets', title: '数据集', icon: Files, roles: ['owner', 'admin'] },
    { index: '/tasks', title: '任务管理', icon: List, roles: ['owner', 'admin'] },
    { index: '/exports', title: '导出记录', icon: Download, roles: ['owner', 'admin'] },
    { index: '/users', title: '用户管理', icon: User, roles: ['owner', 'admin'] },
    { index: '/square', title: '标注广场', icon: DataAnalysis, roles: ['labeler', 'owner', 'admin'] },
    { index: '/review', title: '审核任务', icon: Connection, roles: ['reviewer', 'owner', 'admin'] }
  ]
  const role = auth.user?.role_code
  return all.filter(m => !role || m.roles.includes(role))
})

const activeMenu = computed(() => {
  const p = route.path
  if (p.startsWith('/templates')) return '/templates'
  if (p.startsWith('/datasets')) return '/datasets'
  if (p.startsWith('/tasks')) return '/tasks'
  if (p.startsWith('/square') || p.startsWith('/workbench')) return '/square'
  if (p.startsWith('/review')) return '/review'
  return p
})

function go(index: string) {
  router.push(index)
}

async function handleLogout() {
  await auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <el-icon :size="22"><Tools /></el-icon>
        <span>Buyunaihe</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="side-menu"
        background-color="#1f2430"
        text-color="#c7ccd6"
        active-text-color="#ffffff"
        @select="go"
      >
        <el-menu-item v-for="m in menus" :key="m.index" :index="m.index">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-footer">不奈何 · AI 数据标注平台</div>
    </aside>

    <div class="main">
      <header class="topbar">
        <div class="left">{{ $route.meta.title || auth.user?.nickname || 'Buyunaihe' }}</div>
        <div class="right">
          <el-dropdown @command="(c:string)=>c==='logout'?handleLogout():null">
            <span class="user-chip">
              <el-avatar :size="32" :src="auth.user?.avatar_url">{{ (auth.user?.nickname || auth.user?.username || 'U').slice(0,1) }}</el-avatar>
              <span class="uname">{{ auth.user?.nickname || auth.user?.username }}</span>
              <el-tag size="small" effect="plain" type="primary">{{ auth.user ? ROLE_LABEL[auth.user.role_code] : '' }}</el-tag>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <main class="content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped lang="scss">
.layout { display: flex; height: 100%; }
.sidebar { width: 220px; background: var(--lh-sidebar); color: #c7ccd6; display:flex; flex-direction:column; }
.brand { height: 60px; display:flex; align-items:center; gap:10px; padding-left:22px; font-size:18px; font-weight:700; color:#fff; letter-spacing:0.5px; }
.side-menu { border-right: none; flex:1; }
.side-menu :deep(.el-menu-item) { height: 48px; line-height: 48px; }
.side-menu :deep(.el-menu-item.is-active) { background: var(--lh-primary) !important; }
.sidebar-footer { padding: 14px 22px; font-size: 12px; color: #5b6470; }
.main { flex:1; display:flex; flex-direction:column; background:#f5f7fb; min-width:0; }
.topbar { height:60px; background:#fff; border-bottom:1px solid #eef0f5; display:flex; align-items:center; justify-content:space-between; padding:0 24px; }
.topbar .left { font-size:15px; font-weight:600; color:#1f2430; }
.topbar .right .user-chip { display:flex; align-items:center; gap:8px; cursor:pointer; }
.user-chip .uname { font-size:14px; color:#1f2430; }
.content { flex:1; overflow:auto; }
</style>