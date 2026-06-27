import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import ECharts from 'vue-echarts'
import 'echarts'

import App from './App.vue'
import router from './router'
import { setRouterPush } from './api'
import './styles/main.scss'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)

for (const [key, comp] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, comp as any)
}

app.component('ECharts', ECharts)

setRouterPush((path: string) => {
  router.replace(path)
})

app.mount('#app')