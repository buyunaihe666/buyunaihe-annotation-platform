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
        <el-icon :size="26" color="#6366f1"><Tools /></el-icon>
        <span>不予奈何</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="side-menu"
        :ellipsis="false"
        background-color="#ffffff"
        text-color="#64748b"
        active-text-color="#6366f1"
        @select="go"
      >
        <el-menu-item v-for="m in menus" :key="m.index" :index="m.index">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.title }}</span>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-footer">
        <div class="footer-divider"></div>
        AI 数据标注平台
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <div class="left">{{ $route.meta.title || '工作台' }}</div>
        <div class="right">
          <el-dropdown @command="(c:string)=>c==='logout'?handleLogout():null">
            <span class="user-chip">
              <el-avatar :size="34" :src="auth.user?.avatar_url" :style="{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }">
                {{ (auth.user?.nickname || auth.user?.username || 'U').slice(0,1) }}
              </el-avatar>
              <div class="user-info">
                <span class="uname">{{ auth.user?.nickname || auth.user?.username }}</span>
                <span class="role">{{ auth.user ? ROLE_LABEL[auth.user.role_code] : '' }}</span>
              </div>
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
.sidebar { 
  width: 240px; 
  background: var(--lh-sidebar); 
  color: #64748b; 
  display:flex; 
  flex-direction:column;
  border-right: 1px solid var(--lh-border);
}
.brand { 
  height: 64px; 
  display:flex; 
  align-items:center; 
  gap:12px; 
  padding-left:24px; 
  font-size:20px; 
  font-weight:700; 
  color:var(--lh-text); 
  letter-spacing:-0.5px;
}
.side-menu { border-right: none; flex:1; padding-top: 8px; }
.side-menu :deep(.el-menu-item) { 
  height: 48px; 
  line-height: 48px; 
  margin: 4px 16px;
  border-radius: 8px;
  &:hover { background: #f1f5f9 !important; }
}
.side-menu :deep(.el-menu-item.is-active) { 
  background: var(--lh-primary-light) !important; 
  color: var(--lh-primary) !important;
  font-weight: 600;
}
.sidebar-footer { 
  padding: 20px 24px; 
  font-size: 12px; 
  color: #94a3b8; 
  text-align: center;
}
.footer-divider { 
  height: 1px; 
  background: var(--lh-border); 
  margin-bottom: 16px;
}
.main { flex:1; display:flex; flex-direction:column; background:var(--lh-bg); min-width:0; }
.topbar { 
  height:64px; 
  background:#fff; 
  border-bottom:1px solid var(--lh-border); 
  display:flex; 
  align-items:center; 
  justify-content:space-between; 
  padding:0 32px; 
}
.topbar .left { 
  font-size:16px; 
  font-weight:600; 
  color:var(--lh-text); 
  letter-spacing:-0.3px;
}
.topbar .right .user-chip { 
  display:flex; 
  align-items:center; 
  gap:12px; 
  cursor:pointer;
  padding: 6px 12px;
  border-radius: 10px;
  transition: background 0.2s;
  &:hover { background: #f8fafc; }
}
.user-info { display: flex; flex-direction: column; }
.user-info .uname { 
  font-size:14px; 
  color:var(--lh-text); 
  font-weight: 500;
  line-height: 1.3;
}
.user-info .role { 
  font-size:12px; 
  color:var(--lh-text-soft);
  line-height: 1.3;
}
.content { flex:1; overflow:auto; }
</style>
