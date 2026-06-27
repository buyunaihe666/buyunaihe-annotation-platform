import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/Dashboard.vue'), meta: { roles: ['owner', 'admin', 'labeler', 'reviewer'] } },
      { path: 'templates', name: 'templates', component: () => import('@/views/template/TemplateList.vue'), meta: { roles: ['owner', 'admin'] } },
      { path: 'templates/new', name: 'template-new', component: () => import('@/views/template/TemplateEdit.vue'), meta: { roles: ['owner', 'admin'] } },
      { path: 'templates/:id/preview', name: 'template-preview', component: () => import('@/views/template/TemplatePreview.vue'), meta: { roles: ['owner', 'admin'] } },
      { path: 'templates/:id/edit', name: 'template-edit', component: () => import('@/views/template/TemplateEdit.vue'), meta: { roles: ['owner', 'admin'] } },
      { path: 'datasets', name: 'datasets', component: () => import('@/views/dataset/DatasetList.vue'), meta: { roles: ['owner', 'admin'] } },
      { path: 'datasets/:id', name: 'dataset-detail', component: () => import('@/views/dataset/DatasetDetail.vue'), meta: { roles: ['owner', 'admin'] } },
      { path: 'tasks', name: 'tasks', component: () => import('@/views/task/TaskList.vue'), meta: { roles: ['owner', 'admin'] } },
      { path: 'tasks/new', name: 'task-new', component: () => import('@/views/task/TaskEdit.vue'), meta: { roles: ['owner', 'admin'] } },
      { path: 'tasks/:id/edit', name: 'task-edit', component: () => import('@/views/task/TaskEdit.vue'), meta: { roles: ['owner', 'admin'] } },
      { path: 'tasks/:id', name: 'task-detail', component: () => import('@/views/task/TaskDetail.vue'), meta: { roles: ['owner', 'admin'] } },
      { path: 'exports', name: 'exports', component: () => import('@/views/export/ExportList.vue'), meta: { roles: ['owner', 'admin'] } },
      { path: 'users', name: 'users', component: () => import('@/views/user/UserList.vue'), meta: { roles: ['owner', 'admin'] } },
      { path: 'square', name: 'square', component: () => import('@/views/annotation/Square.vue'), meta: { roles: ['labeler'] } },
      { path: 'workbench/:itemId', name: 'workbench', component: () => import('@/views/annotation/Workbench.vue'), meta: { roles: ['labeler'] } },
      { path: 'review', name: 'review', component: () => import('@/views/review/ReviewTaskList.vue'), meta: { roles: ['reviewer'] } },
      { path: 'review/items/:taskId', name: 'review-items', component: () => import('@/views/review/ReviewTaskItems.vue'), meta: { roles: ['reviewer'] } },
      { path: 'review/workbench/:itemId', name: 'review-workbench', component: () => import('@/views/review/ReviewWorkbench.vue'), meta: { roles: ['reviewer'] } }
    ]
  },
  { path: '/:pathMatch(.*)*', name: 'notfound', component: () => import('@/views/NotFound.vue'), meta: { public: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) return true
  if (!auth.isLoggedIn) return { path: '/login', query: { redirect: to.fullPath } }
  if (!auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      return { path: '/login' }
    }
  }
  const roles = to.meta.roles as string[] | undefined
  if (roles && auth.user && !roles.includes(auth.user.role_code)) {
    return { path: '/' }
  }
  return true
})

export default router