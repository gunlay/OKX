import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'

// 导入页面组件
import Home from './views/Home.vue'
import Transactions from './views/Transactions.vue'
import Tasks from './views/Tasks.vue'
import Settings from './views/Settings.vue'

// 路由配置
const routes = [
  { path: '/', component: Home },
  { path: '/transactions', component: Transactions },
  { path: '/tasks', component: Tasks },
  { path: '/settings', component: Settings }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const app = createApp(App)
app.use(router)
app.mount('#app') 